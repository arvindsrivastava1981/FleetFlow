"""Unit tests for the global error handler & central error-logging sink.

Covers `backend/app/core/errors.py` (ApiError, register_error_handlers, and the
best-effort `_log_error` insert into the `error_logs` table) plus the
`deps._bad` / `_not_found` helpers that now RAISE so every endpoint flows
through the global handlers.
"""

from __future__ import annotations

from unittest import mock

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel

from backend.app.core import errors as err_mod
from backend.app.core.errors import (
    ApiError,
    bad_request,
    not_found,
    register_error_handlers,
)
from backend.app.api.v1.deps import _bad, _not_found


class _ReqBody(BaseModel):
    name: str


def test_bad_request_raises_api_error_with_400():
    """`deps._bad` must RAISE (not return) an ApiError with status 400.

    This is what lets every existing `return _bad(...)` call site flow through
    the global exception handler instead of returning an unlogged JSONResponse.
    """
    with mock.patch.object(err_mod, "_log_error", return_value=None), \
         mock.patch.object(err_mod, "get_db"):
        try:
            _bad("boom", "WHATEVER")
        except ApiError as exc:
            assert exc.status_code == 400
            assert exc.message == "boom"
            assert exc.code == "WHATEVER"
        else:  # pragma: no cover - the helper must raise
            raise AssertionError("_bad() did not raise")


def test_not_found_raises_api_error_with_404():
    with mock.patch.object(err_mod, "_log_error", return_value=None), \
         mock.patch.object(err_mod, "get_db"):
        try:
            _not_found("missing")
        except ApiError as exc:
            assert exc.status_code == 404
            assert exc.message == "missing"
            assert exc.code == "NOT_FOUND"
        else:  # pragma: no cover
            raise AssertionError("_not_found() did not raise")


def test_bad_request_and_not_found_helper_constructors():
    e1 = bad_request("x", code="C1")
    e2 = not_found("y")
    assert e1.status_code == 400 and e1.code == "C1"
    assert e2.status_code == 404 and e2.code == "NOT_FOUND"


@mock.patch.object(err_mod, "_log_error", return_value=None)
def test_register_handlers_and_raise_flow(log_mock: mock.MagicMock):
    """A route that raises ApiError returns the `{error, code}` manual envelope
    and records a log row through the global handler (via a real app)."""
    from backend.app.core.errors import _ET_API

    app = FastAPI()

    @app.get("/boom")
    def _boom(request: Request):
        raise ApiError(400, "bad things", code="BAD_THINGS")

    register_error_handlers(app)
    client = TestClient(app)
    resp = client.get("/boom")

    assert resp.status_code == 400
    assert resp.json() == {"error": "bad things", "code": "BAD_THINGS"}
    # The global handler persists a row in error_logs.
    log_call = log_mock.call_args
    assert log_call.kwargs["status_code"] == 400
    assert log_call.kwargs["error_type"] == _ET_API
    assert log_call.kwargs["message"] == "bad things"

@mock.patch.object(err_mod, "_log_error", return_value=None)
def test_api_error_404_not_persisted(log_mock: mock.MagicMock):
    """A 404 ApiError (e.g. `GET /trips/NOPE` via `_not_found()`) returns the
    same `{error, code}` body but is NOT written to `error_logs` — it is
    ordinary routing-miss junk indistinguishable from the noise already
    suppressed by `_handle_http_error`. Other statuses still log."""
    from backend.app.core.errors import _ET_API

    app = FastAPI()
    register_error_handlers(app)
    client = TestClient(app)

    # 404 NOT_FOUND -> suppressed.
    @app.get("/missing")
    def _missing(request: Request):
        raise not_found("trip not found")

    resp = client.get("/missing")
    assert resp.status_code == 404
    assert resp.json() == {"error": "trip not found", "code": "NOT_FOUND"}
    log_mock.assert_not_called()

    # 400 BAD_REQUEST -> still persisted.
    @app.get("/boom")
    def _boom(request: Request):
        raise bad_request("bad things")

    resp = client.get("/boom")
    assert resp.status_code == 400
    assert log_mock.called
    log_call = log_mock.call_args
    assert log_call.kwargs["status_code"] == 400
    assert log_call.kwargs["error_type"] == _ET_API

@mock.patch.object(err_mod, "_log_error", return_value=None)
def test_validation_error_returns_422_and_logs(log_mock: mock.MagicMock):
    """Request body validation failures (before any DB work) are caught by the
    global validation handler and logged as VALIDATION."""
    from backend.app.core.errors import _ET_VALIDATION

    app = FastAPI()

    @app.post("/validate")
    def _validate(body: _ReqBody):
        return {"ok": True}

    register_error_handlers(app)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.post("/validate", json={})  # missing required "name"

    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_ERROR"
    assert log_mock.called
    log_call = log_mock.call_args
    assert log_call.kwargs["status_code"] == 422
    assert log_call.kwargs["error_type"] == _ET_VALIDATION


@mock.patch.object(err_mod, "get_db")
def test_log_error_inserts_into_error_logs(mock_get_db: mock.MagicMock):
    """`_log_error` writes a fully-parameterized row into error_logs."""
    from backend.app.core.errors import _ET_INTERNAL

    cur = mock.MagicMock()
    cur.execute.return_value = None

    # cur is used as `with conn.cursor() as cur`; Model its __enter__/__exit__.
    cur.__enter__.return_value = cur
    cur.__exit__.return_value = False

    conn = mock.MagicMock()
    conn.cursor.return_value = cur

    # get_db() is called with `with get_db() as conn`.
    db_obj = mock.MagicMock()
    db_obj.__enter__.return_value = conn
    db_obj.__exit__.return_value = False
    mock_get_db.return_value = db_obj

    err_mod._log_error(
        request=None,
        status_code=500,
        error_type=_ET_INTERNAL,
        message="internal server error",
        traceback_text="Traceback (most recent call last):...",
        detail={"exc_type": "RuntimeError", "exc_str": "oops"},
    )

    assert cur.execute.called
    sql, params = cur.execute.call_args[0]
    assert "INSERT INTO error_logs" in sql
    assert params[2] == 500
    assert params[3] == _ET_INTERNAL
    assert params[4] == "internal server error"
    assert "oops" in params[5]


@mock.patch.object(err_mod, "get_db", side_effect=RuntimeError("db down"))
def test_log_error_is_best_effort(_mock_db: mock.MagicMock):
    """A failing log sink must never raise or mask the request error."""
    from backend.app.core.errors import _ET_INTERNAL

    # Should NOT raise even though get_db blows up.
    err_mod._log_error(
        request=None,
        status_code=500,
        error_type=_ET_INTERNAL,
        message="internal server error",
    )
@mock.patch.object(err_mod, "_log_error", return_value=None)
def test_internal_error_surfaces_real_details(log_mock: mock.MagicMock):
    """Uncaught 5xx must return the REAL exception type/message/traceback in the
    response body (production too), not a generic 'internal server error'."""
    from backend.app.core.errors import _ET_INTERNAL

    app = FastAPI()

    @app.get("/crash")
    def _crash(request: Request):
        raise RuntimeError("boom: db connection lost")

    register_error_handlers(app)
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.get("/crash")

    assert resp.status_code == 500
    body = resp.json()
    assert body["code"] == "INTERNAL_ERROR"
    assert body["error"] == "boom: db connection lost"
    assert body["details"]["exc_type"] == "RuntimeError"
    assert "boom: db connection lost" in body["details"]["exc_str"]
    assert "Traceback (most recent call last)" in body["details"]["traceback"]

    log_call = log_mock.call_args
    assert log_call.kwargs["status_code"] == 500
    assert log_call.kwargs["error_type"] == _ET_INTERNAL
    assert log_call.kwargs["message"] == "boom: db connection lost"
    assert "Traceback" in log_call.kwargs["traceback_text"]