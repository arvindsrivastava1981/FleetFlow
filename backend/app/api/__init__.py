"""FastAPI routers for VahanKhata.

Routers map one-to-one with the former top-level routes in
`fleetflow_interactive_demo.py`. Each router file owns all endpoints for a
single feature area and depends on `services.*` + `web/templates.*`.

- dashboard.py        : GET /dashboard (Savings dashboard)
- trips.py            : GET /trips, POST /create-trip, GET /settle-trip
- expenses.py         : GET/POST /simulate-whatsapp, GET /action-expense
- settlement.py       : GET /settled-pdfs, GET /generate-settlement-pdf
- benchmarks.py       : GET/POST fuel-benchmarks page + add/edit/delete
- rules.py            : GET /rule-engine (read-only explainer)
- auth.py             : GET/POST /login, GET /logout
- demo.py             : GET /reset-demo (only dev helper)
- health.py           : GET /healthz, GET / (root landing/dashboard)

Webhook-based future work (Phases C+) lives in:
- whatsapp/webhook.py : POST /whatsapp/webhook (G1)
- ocr/callback.py     : POST /ocr/callback (G2/D)
"""