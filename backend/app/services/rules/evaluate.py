from __future__ import annotations

from dataclasses import dataclass

from backend.app.services.rules.bands import DEFAULT_BAND, FuelBand
from backend.app.services.rules.constants import (
    DEF_MAX_RATIO_PCT,
    DEF_MIN_RATIO_PCT,
    DEF_RATE_MAX,
    MAJOR_REPAIR_THRESHOLD,
    MATH_TOLERANCE,
    MILEAGE_FLOOR_KML,
    TANK_CAPACITY,
)
from backend.app.services.states import STATE_NAME_BY_CODE


def _state_label(state_code: str | None) -> str:
    """Human label for a fueling state, e.g. ``UP / Uttar Pradesh``."""
    if not state_code:
        return "default"
    name = STATE_NAME_BY_CODE.get(state_code.upper())
    return f"{state_code} / {name}" if name else state_code.upper()


@dataclass(frozen=True)
class RuleInput:
    """Context the caller resolves before invoking the engine."""

    exp_type: str
    amount: float
    liters: float = 0.0
    rate: float = 0.0
    odometer: float = 0.0
    prev_odo: float = 0.0
    total_diesel_liters: float = 0.0
    total_def_liters: float = 0.0
    band: FuelBand = DEFAULT_BAND
    band_state_code: str | None = None


@dataclass(frozen=True)
class RuleVerdict:
    """Result of running the engine on a single expense."""

    flagged: bool
    reason: str

    def __bool__(self) -> bool:  # convenience: `if verdict:` works
        return self.flagged


def evaluate_expense(expense: RuleInput) -> RuleVerdict:
    """Return the flag verdict + human reason for a single expense line.

    FUEL checks run in order (short-circuit on first flag):
      1. Math integrity (amount ≈ liters × rate, within MATH_TOLERANCE).
      2. Price band — the rate must fall inside the per-fueling-state benchmark
         band (expense.band, defaulting to DEFAULT_BAND = BENCHMARK_PRICE ± 8%).
         The flag reason names the state that band belongs to (`band_state_code`).
      3. Tank capacity (liters ≤ TANK_CAPACITY).
      4. Odometer rollback vs previous reading + mileage floor
         (km/L ≥ MILEAGE_FLOOR_KML = EXPECTED_KML × 0.7).
    Then TOLL / REPAIR / CHALLAN / DEF / GOODS rules follow.
    Mirrors the original branching order with per-state band + state-aware labels.
    """
    exp_type = expense.exp_type
# ---- FUEL -----------------------------------------------------------
    if exp_type == "FUEL":
        # Rule 1: Mathematical integrity (Amount == Liters * Rate)
        if expense.liters > 0 and expense.rate > 0:
            expected = expense.liters * expense.rate
            if abs(expense.amount - expected) > MATH_TOLERANCE:
                return RuleVerdict(
                    True,
                    f"Math Mismatch: Claimed ₹{expense.amount:,.0f} vs "
                    f"{expense.liters}L @ ₹{expense.rate}/L = ₹{expected:,.0f}",
                )

        # Rule 2: Price band (benchmark +/- tolerance, not hardcoded values)
        if not expense.band.contains(expense.rate):
            return RuleVerdict(
                True,
                f"Rate ₹{expense.rate}/L outside benchmark band "
                f"(₹{expense.band.min_price:.2f} - {expense.band.max_price:.2f}) "
                f"for fueling state {_state_label(expense.band_state_code)}",
            )

        # Rule 3: Tank overflow
        if expense.liters > TANK_CAPACITY:
            return RuleVerdict(
                True,
                f"Quantity {expense.liters}L exceeds max tank capacity ({TANK_CAPACITY}L)",
            )

        # Rule 4: Odometer rollback + mileage floor (context-provided prev_odo)
        if expense.odometer > 0:
            if expense.prev_odo > 0 and expense.odometer < expense.prev_odo:
                return RuleVerdict(
                    True,
                    f"Odometer rollback ({expense.odometer:,.0f} KM < "
                    f"previous {expense.prev_odo:,.0f} KM)",
                )
            if (
                expense.prev_odo > 0
                and expense.odometer > expense.prev_odo
                and expense.liters > 0
            ):
                kml = (expense.odometer - expense.prev_odo) / expense.liters
                if kml < MILEAGE_FLOOR_KML:
                    return RuleVerdict(
                        True,
                        f"Abnormal mileage {kml:.1f} km/L "
                        f"(expected ~{MILEAGE_FLOOR_KML:.1f}+ km/L)",
                    )
        return RuleVerdict(False, "")
# ---- TOLL -------------------------------------------------------------
    if exp_type == "TOLL":
        # Phase A/B/G5 wires corridor lookup here; default = always flag.
        return RuleVerdict(True, "Cash claimed on FASTag-mandated corridor")

    # ---- REPAIR -------------------------------------------------------------
    if exp_type == "REPAIR":
        if expense.amount > MAJOR_REPAIR_THRESHOLD:
            return RuleVerdict(
                True,
                f"Major repair > ₹{MAJOR_REPAIR_THRESHOLD:,.0f} requires owner pre-approval",
            )
        return RuleVerdict(False, "")

    # ---- CHALLAN -------------------------------------------------------------
    if exp_type == "CHALLAN":
        return RuleVerdict(True, "Traffic challan claimed - verify against e-challan portal")
# ---- DEF ---------------------------------------------------------------
    if exp_type == "DEF":
        if expense.rate > DEF_RATE_MAX:
            return RuleVerdict(
                True,
                f"DEF rate ₹{expense.rate}/L exceeds benchmark ceiling "
                f"(₹{DEF_RATE_MAX:.0f}/L) - price inflation",
            )
        if expense.liters > 0:
            total_diesel = expense.total_diesel_liters + expense.liters
            total_def = expense.total_def_liters + expense.liters
            if total_diesel > 0:
                ratio_pct = (total_def / total_diesel) * 100
                if ratio_pct < DEF_MIN_RATIO_PCT or ratio_pct > DEF_MAX_RATIO_PCT:
                    return RuleVerdict(
                        True,
                        f"Abnormal DEF consumption ratio: {ratio_pct:.1f}% of diesel "
                        f"(expected {DEF_MIN_RATIO_PCT:.0f}-{DEF_MAX_RATIO_PCT:.0f}%)",
                    )
        return RuleVerdict(False, "")

    # ---- GOODS (buy/sale) + MISC stay pending for manager review, never auto-flag ----
    if exp_type in ("GOODS_BUY", "GOODS_SALE", "MISC"):
        return RuleVerdict(False, "")

    return RuleVerdict(False, "")
