"""Pydantic v2 request / response contracts.

Validates input at the API boundary and gives FastAPI typed response models that
serialize every `/api/v1` endpoint to a JSON envelope.

- api_v1.py : typed response models for all `/api/v1` JSON endpoints
- *_constants.py: shared enums (ExpenseType, ManagerStatus, TripStatus,
  SystemInvariants) so routers, services and models all reference one source.
"""
