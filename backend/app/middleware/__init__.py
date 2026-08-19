"""Middleware (ASGI) — cross-cutting concerns.

- csrf.py     : CSRF token issue/verify for POST endpoints (fixes §2.4)
- auth.py     : reusable Auth dependency applied to ALL mutation routes
               (fixes the unauthenticated-mutation CRITICAL gap §2.1)
"""
