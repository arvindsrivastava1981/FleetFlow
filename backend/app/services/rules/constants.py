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
# Must stay in sync with the `expenses.exp_type` CHECK constraint in schema.sql.
EXPENSE_TYPES: tuple[str, ...] = (
    "FUEL", "DEF", "TOLL", "REPAIR", "CHALLAN", "MISC", "GOODS_BUY", "GOODS_SALE",
    "CASH_ADVANCE", "DRIVER_SALARY",
)
GOODS_TYPES: tuple[str, ...] = ("GOODS_BUY", "GOODS_SALE")
ALWAYS_FLAG_NON_GOODS_REVIEW: tuple[str, ...] = (
    "TOLL", "CHALLAN",
)
