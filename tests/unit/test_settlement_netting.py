from __future__ import annotations

import pytest

from backend.app.services.audit.cash import (
    DEFAULT_DRIVER_BATTA,
    SettlementResult,
    compute_settlement,
    resolve_trip_batta,
)


def _exp(exp_type="FUEL", amount=100.0, approved_amount=None,
         manager_status="APPROVED", liters=10.0) -> dict:
    return {
        "exp_type": exp_type,
        "amount": amount,
        "approved_amount": approved_amount,
        "liters": liters,
        "manager_status": manager_status,
        "is_flagged": False,
        "odometer": 1000.0,
        "rate": 90.50,
    }


def _trip(**kw) -> dict:
    base = {
        "trip_code": "TRIP-101",
        "advance_amount": 10000.0,
        "start_odo": 100000.0,
        "end_odo": 100500.0,
        "current_odo": 100500.0,
        "driver_batta_amount": DEFAULT_DRIVER_BATTA,
    }
    base.update(kw)
    return base


# ---- 1. COALESCE(approved_amount, amount) --------------------------------
def test_approved_amount_fallback_to_amount_when_none():
    """When approved_amount is unset, the full claim amount is used."""
    expenses = [_exp(exp_type="FUEL", amount=2715.0, liters=30.0)]
    s = compute_settlement(_trip(), expenses)
    assert s.expense_buckets["FUEL"] == 2715.0


def test_approved_amount_wins_over_amount_when_set():
    """A partial deduction (approved_amount < amount) is honoured."""
    expenses = [_exp(exp_type="REPAIR", amount=5000.0, approved_amount=3500.0)]
    s = compute_settlement(_trip(), expenses)
    assert s.expense_buckets["REPAIR"] == 3500.0


def test_pending_and_rejected_expenses_excluded():
    """Only strictly-APPROVED expenses enter the settlement math."""
    expenses = [
        _exp(exp_type="FUEL", amount=1000.0, manager_status="APPROVED"),
        _exp(exp_type="FUEL", amount=2000.0, manager_status="PENDING"),
        _exp(exp_type="FUEL", amount=3000.0, manager_status="REJECTED"),
    ]
    s = compute_settlement(_trip(), expenses)
    assert s.expense_buckets["FUEL"] == 1000.0


# ---- 2. GOODS_SALE credits to Cr; CHALLAN debits to Dr -------------------
def test_goods_sale_credits_to_cr():
    """GOODS_SALE increases total_cr, never the debit buckets."""
    expenses = [_exp(exp_type="GOODS_SALE", amount=8000.0)]
    s = compute_settlement(_trip(advance_amount=10000.0), expenses)
    assert s.goods_income == 8000.0
    assert s.total_cr == 18000.0          # advance + goods sale
    assert s.expense_buckets.get("GOODS_SALE", 0) == 0.0  # not a debit bucket
    assert all(k != "GOODS_SALE" for k in s.expense_buckets)


def test_challan_debits_to_dr():
    """CHALLAN lands in a dedicated debit bucket."""
    expenses = [_exp(exp_type="CHALLAN", amount=1200.0)]
    s = compute_settlement(_trip(), expenses)
    assert s.expense_buckets["CHALLAN"] == 1200.0
    assert s.total_road_expenses == 1200.0


def test_advance_plus_batta_refund_scenario():
    """Advance-only trip (no expenses) -> driver refunds to fleet."""
    s = compute_settlement(_trip(advance_amount=10000.0), [])
    assert s.total_driver_credits == 2500.0      # just batta
    assert s.net_balance == pytest.approx(7500.0)
    assert s.is_driver_refund is True
    assert s.status_label_en == "REFUNDABLE TO FLEET"
    assert s.status_label_hi == "चालक द्वारा कंपनी को वापसी"


def test_fully_settled_when_balanced():
    """When Cr == Dr the status is FULLY SETTLED."""
    expenses = [_exp(exp_type="FUEL", amount=2500.0, liters=25.0)]
    s = compute_settlement(_trip(advance_amount=5000.0), expenses)
    # 5000 (advance) == 2500 (fuel) + 2500 (batta) -> zero
    assert s.net_balance == 0.0
    assert s.status_label_en == "FULLY SETTLED"
    assert s.status_label_hi == "पूर्ण हिसाब बराबर"
    assert s.is_driver_refund is False


# ---- 3. driver_batta_amount = 0.00 handling ------------------------------
def test_zero_batta_when_driver_batta_amount_zero():
    """A 0.00 batta (e.g. batta_type 'NONE') must not fall back to default."""
    s = compute_settlement(_trip(advance_amount=1000.0, driver_batta_amount=0.00), [])
    assert s.driver_batta == 0.0
    assert s.total_driver_credits == 0.0
    assert s.net_balance == 1000.0


def test_resolve_trip_batta_none_profile_returns_zero():
    """resolve_trip_batta maps batta_type 'NONE' -> 0.00."""
    assert resolve_trip_batta({"batta_type": "NONE", "default_batta_rate": 2500.0}) == 0.0


def test_resolve_trip_batta_uses_default_rate():
    assert resolve_trip_batta({"batta_type": "FIXED_TRIP", "default_batta_rate": 3000.0}) == 3000.0


def test_resolve_trip_batta_defaults_when_no_profile():
    assert resolve_trip_batta(None) == DEFAULT_DRIVER_BATTA
    assert resolve_trip_batta({"batta_type": "FIXED_TRIP", "default_batta_rate": None}) == DEFAULT_DRIVER_BATTA


# ---- 4. Division-by-zero protection on avg_kml ---------------------------
def test_avg_kml_none_when_no_fuel():
    s = compute_settlement(_trip(), [])
    assert s.avg_kml is None


def test_avg_kml_none_when_zero_distance():
    # distance == 0 -> avoid meaningless infinite mileage
    s = compute_settlement(
        _trip(start_odo=100000.0, end_odo=100000.0),
        [_exp(exp_type="FUEL", liters=25.0)],
    )
    assert s.avg_kml is None


def test_avg_kml_computed_from_fuel_liters():
    s = compute_settlement(
        _trip(start_odo=100000.0, end_odo=100500.0),
        [_exp(exp_type="FUEL", liters=25.0)],
    )
    assert s.avg_kml == 20.0  # 500 km / 25 L


# ---- 5. Hash determinism / sensitivity -----------------------------------
def test_verification_hash_deterministic():
    trip = _trip()
    expenses = [_exp(exp_type="FUEL", amount=100.0)]
    a = compute_settlement(trip, expenses).verification_hash
    b = compute_settlement(trip, expenses).verification_hash
    assert a == b
    assert len(a) == 32


def test_verification_hash_changes_when_input_changes():
    base = _trip(advance_amount=10000.0)
    expenses = []
    h1 = compute_settlement(base, expenses).verification_hash
    h2 = compute_settlement(_trip(advance_amount=15000.0), expenses).verification_hash
    assert h1 != h2


def test_settlement_result_type():
    s = compute_settlement(_trip(), [])
    assert isinstance(s, SettlementResult)


# ---- Batta profile normalisation (users.py `_normalise_batta`) ------------
def test_normalise_batta_defaults():
    from backend.app.db.queries.users import _normalise_batta
    assert _normalise_batta(None, None) == ("FIXED_TRIP", 2500.00)
    assert _normalise_batta("", "") == ("FIXED_TRIP", 2500.00)


def test_normalise_batta_whitelist_and_rate():
    from backend.app.db.queries.users import _normalise_batta
    assert _normalise_batta("none", "0.00") == ("NONE", 0.00)
    assert _normalise_batta("fixed_trip", "3000") == ("FIXED_TRIP", 3000.00)


def test_normalise_batta_rejects_unknown_type():
    from backend.app.db.queries.users import _normalise_batta
    # Unknown type falls back to FIXED_TRIP, keeps a valid rate.
    assert _normalise_batta("WEEKLY", "1800") == ("FIXED_TRIP", 1800.00)