"""Pydantic v2 request / response contracts.

Validates input at the API boundary (fixes the current "no input validation"
gap) and gives FastAPI typed response models that serialize to the templates.

- auth.py      : LoginForm, SessionPayload
- trips.py     : TripCreate, TripView
- expenses.py  : ExpenseCreate, ExpenseAction, ExpenseView
- benchmarks.py: FuelBenchmarkUpsert
- *_constants.py: shared enums (ExpenseType, ManagerStatus, TripStatus,
  SystemInvariants) so routers, services and models all reference one source.
"""