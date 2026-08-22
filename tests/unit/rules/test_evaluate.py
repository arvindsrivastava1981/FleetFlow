from __future__ import annotations

import pytest

from backend.app.services.rules.bands import derive_band
from backend.app.services.rules.constants import (
    MILEAGE_FLOOR_KML,
    TANK_CAPACITY,
)
from backend.app.services.rules.evaluate import RuleInput, evaluate_expense

BAND = derive_band(90.50, 0.08)


def fuel(**kw) -> RuleInput:
    """Build a FUEL RuleInput with sensible defaults."""
    base = dict(
        exp_type="FUEL", amount=2715.0, liters=30.0, rate=90.50,
        odometer=1000.0, prev_odo=880.0,
    )
    base.update(kw)
    return RuleInput(**base)


def test_clean_fuel_not_flagged():
    assert not evaluate_expense(fuel()).flagged


def test_math_mismatch_flags():
    verdict = evaluate_expense(fuel(amount=9999.0))
    assert verdict.flagged
    assert "Math Mismatch" in verdict.reason


def test_rate_above_band_flags():
    verdict = evaluate_expense(fuel(rate=99.0, amount=2970.0))
    assert verdict.flagged
    assert "benchmark band" in verdict.reason


def test_rate_below_band_flags():
    verdict = evaluate_expense(fuel(rate=80.0, amount=2400.0))
    assert verdict.flagged


def test_band_edges_not_flagged():
    # 83.26 and 97.74 are inclusive bounds -> not flagged
    assert not evaluate_expense(fuel(rate=83.26, amount=2497.8)).flagged
    assert not evaluate_expense(fuel(rate=97.74, amount=2932.2)).flagged


def test_tank_overflow_flags():
    # 351.0 L @ 90.50 => amount 31,765.5 (consistent so math rule passes first)
    verdict = evaluate_expense(
        fuel(liters=TANK_CAPACITY + 1, amount=31765.5)
    )
    assert verdict.flagged
    assert "exceeds max tank capacity" in verdict.reason


def test_mileage_below_floor_flags():
    # 100 km over 40 L = 2.5 km/L < 2.8 floor; 40L @ 90.50 = 3620
    verdict = evaluate_expense(
        fuel(liters=40.0, amount=3620.0, odometer=980.0, prev_odo=880.0)
    )
    assert verdict.flagged
    assert "Abnormal mileage" in verdict.reason


def test_odometer_rollback_flags():
    verdict = evaluate_expense(fuel(odometer=850.0, prev_odo=880.0))
    assert verdict.flagged
    assert "rollback" in verdict.reason


def test_mileage_floor_matches_spec():
    assert MILEAGE_FLOOR_KML == pytest.approx(2.8)


def test_def_rate_above_ceiling_flags():
    verdict = evaluate_expense(
        RuleInput(exp_type="DEF", amount=600.0, liters=10.0, rate=78.0)
    )
    assert verdict.flagged
    assert "ceiling" in verdict.reason


def test_def_ratio_within_range_ok():
    # 4 L DEF on 100 L diesel = 4% (inside 3-6%)
    verdict = evaluate_expense(
        RuleInput(
            exp_type="DEF", amount=240.0, liters=4.0, rate=60.0,
            total_diesel_liters=100.0, total_def_liters=0.0,
        )
    )
    assert not verdict.flagged


def test_repair_below_threshold_ok():
    verdict = evaluate_expense(RuleInput(exp_type="REPAIR", amount=1500.0))
    assert not verdict.flagged


def test_repair_above_threshold_flags():
    verdict = evaluate_expense(RuleInput(exp_type="REPAIR", amount=5000.0))
    assert verdict.flagged
    assert "pre-approval" in verdict.reason


def test_toll_always_flags_pre_corridor():
    verdict = evaluate_expense(RuleInput(exp_type="TOLL", amount=120.0))
    assert verdict.flagged


def test_goods_stay_below_flag_lid():
    # Goods buys/sales are never auto-flagged; they await manager review.
    assert not evaluate_expense(RuleInput(exp_type="GOODS_BUY", amount=9000.0)).flagged
    assert not evaluate_expense(RuleInput(exp_type="GOODS_SALE", amount=12000.0)).flagged


def test_band_reason_names_fueling_state():
    # A TS truck refueling in TS: a legit high TS rate stays in the TS band.
    mp_band = derive_band(103.82, 0.08)  # Telangana ~103.82
    verdict = evaluate_expense(
        fuel(rate=103.80, amount=3114.0, band=mp_band, band_state_code="TS")
    )
    assert not verdict.flagged

    # Same rate judged against the (wrong) home-state band -> flagged, and the
    # reason names the fueling state so the manager sees which band applied.
    home_up = derive_band(95.36, 0.08)
    verdict = evaluate_expense(
        fuel(rate=103.80, amount=3114.0, band=home_up, band_state_code="TS")
    )
    assert verdict.flagged
    assert "benchmark band" in verdict.reason
    assert "TS" in verdict.reason


def test_default_band_reason_when_no_state():
    verdict = evaluate_expense(fuel(rate=99.0, amount=2970.0, band=BAND))
    assert verdict.flagged
    assert "default" in verdict.reason
