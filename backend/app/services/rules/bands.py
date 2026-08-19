from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FuelBand:
    """Inclusive [min, max] per-liter band derived from a benchmark price."""

    benchmark: float
    tolerance_pct: float
    min_price: float
    max_price: float

    def contains(self, rate: float) -> bool:
        """True when `rate` is inside the inclusive band (or is 0 / unknown)."""
        if rate <= 0:
            return True  # zero/unknown rate is not a band violation
        return self.min_price <= rate <= self.max_price


def derive_band(benchmark: float, tolerance_pct: float) -> FuelBand:
    """Build the inclusive [min, max] fuel-price band for a benchmark."""
    return FuelBand(
        benchmark=benchmark,
        tolerance_pct=tolerance_pct,
        min_price=benchmark * (1.0 - tolerance_pct),
        max_price=benchmark * (1.0 + tolerance_pct),
    )


DEFAULT_BAND = derive_band(90.50, 0.08)  # 90.50 ± 8% -> 83.26 .. 97.74