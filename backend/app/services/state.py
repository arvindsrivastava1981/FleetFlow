"""Indian state derivation from a vehicle plate prefix.

Indian plates carry a 2-letter RTO state code as their first segment
(``UP32TA1234`` -> ``UP``). This module maps that prefix to the canonical
``state_code`` used by the ``fuel_benchmarks`` table so the rules engine can
resolve a per-state fuel band from the registered vehicle's plate.
"""

from __future__ import annotations


def state_code_from_plate(plate: str) -> str | None:
    """Return the 2-letter state prefix of a validated plate, uppercased.

    Returns ``None`` when the plate is blank or too short to carry a state
    prefix. Callers are expected to have already validated the plate shape via
    the system ``PLATE_REGEX``; this is a lenient best-effort extraction.
    """
    if not plate:
        return None
    prefix = plate.strip().upper()[:2]
    return prefix if len(prefix) == 2 and prefix.isalpha() else None
