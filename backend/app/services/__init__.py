"""Business logic services.

Every rule or external integration is a package with pure functions that take
plain inputs and return plain results — no FastAPI/Request/HTML coupling. This
is the layer the future Phases C–E (WhatsApp, OCR, EXIF) plug into.

- rules/        : the anomaly engine. `evaluate.py` = evaluate_rules(),
                  `bands.py` = benchmark-driven fuel band, `constants.py` =
                  thresholds (BENCHMARK_PRICE, TANK_CAPACITY, ...)
- audit/        : settlement math (net cash, trip profit, flagged vs approved),
                  reconciliation ledger, savings derivation
- pdf/          : settlement/reconciliation PDF generation (reportlab),
                  future driver-verification slip
- whatsapp/     : Cloud API client + webhook + templates (Phase C)
- ocr/          : receipt/odometer vision parsing + post-processing (Phase D)
- notify/       : bilingual (hi/en) + audio confirmation strings (Phase E)
"""