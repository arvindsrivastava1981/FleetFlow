"""Entitlement resolution for the "fleet = transport firm" model.

Every permission gate (vehicle limit, driver limit, future feature flags) reads
through :func:`fleet_feature`. A fleet's effective capability for a feature is:

    plan_feature_value  + fleet_addon_value

where the plan feature comes from the plan's ``features`` JSONB capability matrix
and the fleet add-on is any extra bought capacity in ``fleets.entitlement_addons``
(e.g. purchased extra vehicle slots). Keeping this in ONE service means adding a
new product dimension (driver seats, WhatsApp, reports, OCR, ...) is a data edit
+ a thin check here, never a schema/column migration.

Functions follow the query-layer convention: they take a ``conn`` and never open
their own session, so callers (API routers) keep an explicit transactional scope.
"""

from __future__ import annotations

from backend.app.db.queries.fleets import (
    count_active_vehicles,
    get_plan_by_code,
    get_plan_by_id,
)

DEFAULT_FEATURES: dict = {"vehicle_limit": 1, "driver_limit": 1}


def _merged_features(entitlement: dict | None, conn, plan_code: str | None) -> dict:
    """Merge the plan feature set with fleet add-ons (add-on wins on same key)."""
    merged = dict(DEFAULT_FEATURES)
    if plan_code:
        plan = get_plan_by_code(conn, plan_code)
        plan_features = (plan or {}).get("features") or {}
        for key, value in plan_features.items():
            merged[key] = value
    addons = (entitlement or {}).get("entitlement_addons") or {}
    for key, value in addons.items():
        merged[key] = value
    return merged


def fleet_feature(conn, fleet_id: int, feature: str):
    """Return the effective value of *feature* for a fleet (plan + add-ons).

    Falls back to the fleet's plain ``vehicle_limit`` column if no actionable
    features exist yet, so an upgraded DB keeps working against seed data.
    """
    from backend.app.db.queries.fleets import get_fleet_by_id

    fleet = get_fleet_by_id(conn, fleet_id)
    if fleet is None:
        return None
    plan_code = fleet.get("plan_code")
    if not plan_code and fleet.get("plan_id"):
        # get_fleet_by_id returns a raw fleet row (no joined plan_code), so
        # resolve the plan by its numeric id — never by code (that would hit a
        # varchar=integer mismatch on the code column).
        plan = get_plan_by_id(conn, fleet.get("plan_id"))
        plan_code = (plan or {}).get("code")
    merge = _merged_features(fleet, conn, plan_code)
    if feature not in merge:
        # Back-compat: honour the legacy single vehicle_limit column.
        if feature == "vehicle_limit":
            return fleet.get("vehicle_limit", DEFAULT_FEATURES["vehicle_limit"])
        return DEFAULT_FEATURES.get(feature)
    return merge.get(feature)


def fleet_can_add_vehicles(conn, fleet_id: int, entitlement: dict | None) -> tuple[bool, str]:
    """Entitlement gate for adding a vehicle.

    Returns ``(allowed, reason)`` where *reason* is either:
      * ``"OK"``            — fleet is entitled and under its vehicle cap
      * ``"NOT_ENTITLED"``  — no active/trial entitlement (route to billing)
      * ``"NO_FLEET"``      — fleet does not exist
      * ``"VEHICLE_LIMIT"`` — entitled but at capacity (buy a slot)

    Splitting NOT_ENTITLED from VEHICLE_LIMIT turns the opaque 402 into a guided
    UX (G3): the UI shows "start subscription" vs "buy a slot".
    """
    if entitlement is None:
        return False, "NO_FLEET"
    status = entitlement.get("subscription_status")
    if status not in ("ACTIVE", "TRIAL"):
        return False, "NOT_ENTITLED"
    limit = fleet_feature(conn, fleet_id, "vehicle_limit")
    limit = limit or entitlement.get("vehicle_limit") or 1
    used = count_active_vehicles(conn, fleet_id)
    if used < int(limit):
        return True, "OK"
    return False, "VEHICLE_LIMIT"
