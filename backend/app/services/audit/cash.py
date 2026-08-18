"""Single-source settlement netting engine.

Consolidates all trip netting math that previously lived (duplicated) in
`services/pdf/settlement.py` and `api/views.py`. Pure function: takes the trip
row + its expenses, returns a deterministic `SettlementResult` with the Dr/Cr
double-entry balance, driver batta, mileage and a tamper-evident fingerprint.

Closes deep_agent_recommendation §2.6 / §2.9: single named helper, strict
"APPROVED only" definition, `COALESCE(approved_amount, amount)` fallback.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

# Expense buckets debited against the driver's advance (GOODS_SALE is a credit).
ROAD_EXPENSE_BUCKETS: tuple[str, ...] = (
    "FUEL", "DEF", "TOLL", "REPAIR", "CHALLAN", "MISC", "GOODS_BUY",
)

DEFAULT_DRIVER_BATTA = 2500.00


@dataclass
class SettlementResult:
    advance_amount: float
    goods_income: float
    total_cr: float                      # advance_amount + goods_income
    expense_buckets: dict[str, float]    # FUEL, DEF, TOLL, REPAIR, CHALLAN, MISC, GOODS_BUY
    total_road_expenses: float           # Sum of approved expenses (excluding GOODS_SALE)
    driver_batta: float                  # Resolved batta (e.g. 2500.00, or 0.00 if NONE)
    total_driver_credits: float          # total_road_expenses + driver_batta (Total Dr)
    net_balance: float                   # total_cr - total_driver_credits
    is_driver_refund: bool               # True if net_balance > 0 (Driver owes Fleet)
    status_label_en: str                 # REFUNDABLE TO FLEET / PAYABLE TO DRIVER / FULLY SETTLED
    status_label_hi: str                 # चालक द्वारा कंपनी को वापसी / कंपनी द्वारा चालक को देय / पूर्ण हिसाब बराबर
    avg_kml: float | None                # (end_odo - start_odo) / fuel_liters (guarded div/0)
    verification_hash: str               # 32-char uppercase SHA256 hex fingerprint


def resolve_trip_batta(driver: dict | None) -> float:
    """Resolve the driver batta to snapshot onto a trip at creation time.

    - `batta_type == 'NONE'`  -> 0.00 (explicit "no batta" profile)
    - explicit `default_batta_rate` -> that amount
    - otherwise the flat ₹{DEFAULT_DRIVER_BATTA:,.0f} default.

    *driver* is the `users` row (or None when no driver user is linked).
    """
    if not driver:
        return DEFAULT_DRIVER_BATTA
    if (driver.get("batta_type") or "FIXED_TRIP") == "NONE":
        return 0.00
    rate = driver.get("default_batta_rate")
    if rate is None or rate == "":
        return DEFAULT_DRIVER_BATTA
    return round(float(rate), 2)


def _get_effective_amount(expense: dict) -> float:
    """COALESCE(approved_amount, amount) — honors a partial deduction when set."""
    val = expense.get("approved_amount")
    if val is None or val == "":
        val = expense.get("amount")
    return round(float(val or 0.0), 2)


def compute_settlement(trip: dict, expenses: list[dict]) -> SettlementResult:
    """Compute the full Dr/Cr settlement for a trip from its expenses."""
    advance = round(float(trip.get("advance_amount") or 0.0), 2)

    # Strict definition: only manager-APPROVED rows enter the settlement math.
    approved = [e for e in expenses if e.get("manager_status") == "APPROVED"]

    # 1. Goods Income (Credit) — cash the driver collected / returned via sales.
    goods_income = round(sum(
        _get_effective_amount(e) for e in approved if e.get("exp_type") == "GOODS_SALE"
    ), 2)

    # 2. Road Outflow Buckets (Debit) + accumulated FUEL liters for km/L.
    expense_buckets: dict[str, float] = {b: 0.0 for b in ROAD_EXPENSE_BUCKETS}
    fuel_liters = 0.0
    for e in approved:
        etype = e.get("exp_type")
        amt = _get_effective_amount(e)
        if etype in expense_buckets:
            expense_buckets[etype] = round(expense_buckets[etype] + amt, 2)
        if etype == "FUEL":
            fuel_liters += float(e.get("liters") or 0.0)

    total_road_expenses = round(sum(expense_buckets.values()), 2)

    # 3. Driver Batta — resolved at trip-creation and stored on the trip row;
    #    fall back to the flat rate when the column is absent/NULL.
    raw_batta = trip.get("driver_batta_amount")
    driver_batta = round(float(raw_batta), 2) if raw_batta is not None else DEFAULT_DRIVER_BATTA

    # 4. Balancing.
    total_cr = round(advance + goods_income, 2)
    total_driver_credits = round(total_road_expenses + driver_batta, 2)
    net_balance = round(total_cr - total_driver_credits, 2)

    # 5. Status labels (bilingual).
    if net_balance > 0:
        is_driver_refund = True
        status_label_en = "REFUNDABLE TO FLEET"
        status_label_hi = "चालक द्वारा कंपनी को वापसी"
    elif net_balance < 0:
        is_driver_refund = False
        status_label_en = "PAYABLE TO DRIVER"
        status_label_hi = "कंपनी द्वारा चालक को देय"
    else:
        is_driver_refund = False
        status_label_en = "FULLY SETTLED"
        status_label_hi = "पूर्ण हिसाब बराबर"

    # 6. Mileage (guarded against div-by-zero / zero-run).
    start_odo = float(trip.get("start_odo") or 0.0)
    end_odo = float(trip.get("end_odo") or trip.get("current_odo") or 0.0)
    distance = end_odo - start_odo
    avg_kml = round(distance / fuel_liters, 2) if (fuel_liters > 0 and distance > 0) else None

    # 7. Tamper-evident fingerprint (deterministic — excludes settled_at so it
    #    is reproducible for verification against the persisted voucher code).
    raw_hash_input = (
        f"{trip.get('trip_code')}|{advance}|{goods_income}|"
        f"{total_road_expenses}|{driver_batta}|{net_balance}"
    )
    verification_hash = hashlib.sha256(raw_hash_input.encode("utf-8")).hexdigest()[:32].upper()

    return SettlementResult(
        advance_amount=advance,
        goods_income=goods_income,
        total_cr=total_cr,
        expense_buckets=expense_buckets,
        total_road_expenses=total_road_expenses,
        driver_batta=driver_batta,
        total_driver_credits=total_driver_credits,
        net_balance=net_balance,
        is_driver_refund=is_driver_refund,
        status_label_en=status_label_en,
        status_label_hi=status_label_hi,
        avg_kml=avg_kml,
        verification_hash=verification_hash,
    )