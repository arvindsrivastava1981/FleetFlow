"""FastAPI routers for VahanKhata.

The backend is a pure JSON API. Only two routers are mounted:

- api_v1.py     : the `/api/v1/*` JSON API consumed by the web app + mobile
- webhook.py    : `POST /billing/webhook` — Razorpay server-to-server callback

All UI lives in separate web-client services. Legacy server-rendered HTML routers
were removed.
"""
