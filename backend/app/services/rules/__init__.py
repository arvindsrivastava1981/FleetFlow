"""Anomaly Rules Engine.

Extracted verbatim from `evaluate_rules()` in `utils.py` (moves become pure,
testable functions with no cursor/HTTP coupling).

- constants.py : BENCHMARK_PRICE, TANK_CAPACITY, EXPECTED_KML,
                 DEF_RATE_MAX, DEF_MIN/MAX_RATIO_PCT, MATH_TOLERANCE, ...
- bands.py     : derive price band from benchmark + tolerance (fixes hardcoded
                 82/98 drift; Phase A wires per-state `fuel_benchmarks`)
- evaluate.py  : evaluate_rules(expense, previous_odo, benchmarks) -> verdict
- toll.py      : corridor-aware TOLL rule (Phase A/B, G5)
- evidence.py  : dual-photo / EXIF enforcement for FUEL+REPAIR (Phase A/B)
"""
