"""Settlement PDF generation (reportlab).

Moved from `/generate-settlement-pdf` in `fleetflow_interactive_demo.py`.
Kept as a dependency-injectable renderer so it can be unit-tested against
synthetic trip/expense data without touching the DB.
"""