"""Rules-engine constants — single source of truth.

Centralises the magic numbers currently hardcoded across `utils.py` and
`fleetflow_interactive_demo.py`. Routers, services and tests import from here
(NOT from a mix of globals) so a change in a threshold is reflected everywhere.
"""
from __future__ import annotations

from backend.app.core.config import settings

# ---- Fuel band ----------------------------------------------------------
BENCHMARK_PRICE: float = settings.benchmark_price
FUEL_BAND_TOLERANCE_PCT: float = settings.fuel_band_tolerance_pct

# ---- Tank / mileage ------------------------------------------------------
TANK_CAPACITY: float = settings.tank_capacity_liters
EXPECTED_KML: float = settings.expected_kml
MILEAGE_FLOOR_KML: float = EXPECTED_KML * 0.70  # 2.8 km/L hard floor
MATH_TOLERANCE: float = settings.math_tolerance

# ---- DEF audit -----------------------------------------------------------
DEF_RATE_MAX: float = settings.def_rate_max
DEF_MIN_RATIO_PCT: float = settings.def_min_ratio_pct
DEF_MAX_RATIO_PCT: float = settings.def_max_ratio_pct

# ---- Repair threshold ------------------------------------------------------
MAJOR_REPAIR_THRESHOLD: float = 3000.0

# ---- System Invariants ------------------------------------------------------
PLATE_REGEX: str = settings.plate_regex
COUNTRY_CODE: str = settings.country_code
QR_CODE_LENGTH: int = settings.qr_code_length
ANTI_SPAM_SCANS_PER_HOUR: int = settings.anti_spam_scans_per_hour

# ---- Expense domains --------------------------------------------------------
EXPENSE_TYPES: tuple[str, ...] = (
    "FUEL", "TOLL", "REPAIR", "OTHER", "CHALLAN", "MISC",
    "RTO-FINE", "DEF", "GOODS_BUY", "GOODS_SALE",
)
GOODS_TYPES: tuple[str, ...] = ("GOODS_BUY", "GOODS_SALE")
ALWAYS_FLAG_NON_GOODS_REVIEW: tuple[str, ...] = (
    "TOLL", "CHALLAN", "RTO-FINE",
)