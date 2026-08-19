"""Global error handling & central error-logging sink.

Every backend error (ApiError, validation failures, raised HTTP errors, or any
uncaught 5xx) flows through the handlers registered by
:func:`register_error_handlers`, which normalize it to ``{error, code}`` JSON
and persist a row in the ``error_logs`` table. Logging is BEST-EFFORT: if the
DB write fails, the original error response is still returned.
"""

from __future__ import annotations

import json
import logging
import traceback
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.db.connection import get_db

logger = logging.getLogger(__name__)

_SOURCE_BACKEND = "BACKEND"
_ET_API = "API_ERROR"          # ApiError raised by an endpoint / helper
_ET_VALIDATION = "VALIDATION"  # FastAPI request body/query/path validation
_ET_HTTP = "HTTP_ERROR"        # plain HTTPException (e.g. raised 401/404)
_ET_INTERNAL = "INTERNAL"      # uncaught 500 exception


class ApiError(Exception):
    """Domain error carrying an HTTP status + stable machine code.

    Raise from an endpoint instead of returning a JSONResponse; the global
    handler converts it to ``{error, code}`` and logs it to ``error_logs``.
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        code: str = "API_ERROR",
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.code = code
        self.details = details


def bad_request(
    message: str, code: str = "BAD_REQUEST", details: Any | None = None
) -> ApiError:
    return ApiError(400, message, code, details)


def not_found(
    message: str = "not found", code: str = "NOT_FOUND", details: Any | None = None
) -> ApiError:
    return ApiError(404, message, code, details)


def _endpoint_json(status_code: int, message: str, code: str,
                   details: Any | None = None) -> JSONResponse:
    body: dict[str, Any] = {"error": message, "code": code}
    if details is not None:
        body["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def _log_error(*, request: Request | None, status_code: int, error_type: str,
               message: str, detail: Any | None = None,
               traceback_text: str | None = None, endpoint: str | None = None,
               source: str = _SOURCE_BACKEND) -> None:
    """Persist one error row into ``error_logs`` (best-effort, never raises)."""
    try:
        method = getattr(request, "method", None) if request is not None else None
        path = None
        if request is not None:
            url = getattr(request, "url", None)
            path = url.path if url is not None else None
        detail_json = json.dumps(detail, default=str) if detail is not None else None
    except Exception:  # noqa: BLE001
        method, path, detail_json = None, None, None

    # Surface the real failure to the application log stream (visible in the
    # deploy platform's log dashboard in production) as well as the DB sink.
    logger.error(
        "[error_log] %s %s -> %s (%s) message=%s detail=%s",
        method,
        path,
        status_code,
        error_type,
        message,
        detail_json,
    )
    if traceback_text:
        logger.error("[error_log] traceback:\n%s", traceback_text)

    try:
        with get_db() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO error_logs
                    (method, path, status_code, error_type, message, detail,
                     traceback_text, endpoint, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (method, path, status_code, error_type, message, detail_json,
                 traceback_text, endpoint, source),
            )
    except Exception:  # noqa: BLE001 - logging is best-effort
        pass


# -- Exception handlers ---------------------------------------------------------

async def _handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
    # ---- Routing-miss noise guard (mirrors _handle_http_error) -------------
    # An ApiError raised for a non-existent resource (e.g. `GET /trips/NOPE`
    # via `_not_found()` → 404) is indistinguishable from ordinary web junk and
    # probe traffic. Persisting every one of these rows floods `error_logs` and
    # buries real defects; the client still gets the exact same `{error, code}`
    # 404 JSON. Every other status this handler sees (400/401/403/409 and any
    # ApiError-based 5xx) is still logged exactly as before.
    _log_it = not (exc.status_code == 404 or exc.status_code == 405)
    if _log_it:
        _log_error(request=request, status_code=exc.status_code, error_type=_ET_API,
                   message=exc.message,
                   detail={"code": exc.code, "details": exc.details})
    return _endpoint_json(exc.status_code, exc.message, exc.code)


async def _handle_validation_error(request: Request,
                                   exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    fmt = [
        {"loc": [str(loc) for loc in err.get("loc", [])],
         "msg": err.get("msg"), "type": err.get("type")}
        for err in errors
    ]
    _log_error(request=request, status_code=422, error_type=_ET_VALIDATION,
               message="request validation error", detail=fmt)
    return _endpoint_json(422, "request validation error", "VALIDATION_ERROR", details=fmt)


async def _handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # ---- Routing-miss noise guard -------------------------------------------
    # A 404 (path not registered server-side or a missing static asset) and a
    # 405 (a valid-looking path but a method that isn't registered, e.g. a POST
    # to a removed GET-only SPA route) are normal, frequent web traffic — the
    # SPA catch-all and the static-assets mount both provoke them for junk and
    # probe requests, and the JSON API raises them via ApiError (a separate,
    # always-logged handler) in every real call. Persisting every one of these
    # floods `error_logs` with thousands of meaningless rows and hides the real
    # defects. We keep the exact same HTTP response for the client; we just stop
    # persisting these two routing-miss codes. Every other status (incl. auth
    # 401/403 and all 5xx) still gets logged exactly as before.
    _log_it = not (exc.status_code == 404 or exc.status_code == 405)
    if _log_it:
        _log_error(request=request, status_code=exc.status_code, error_type=_ET_HTTP,
                   message=str(exc.detail))
    return _endpoint_json(exc.status_code, str(exc.detail), "HTTP_ERROR")


async def _handle_internal_error(request: Request, exc: Exception) -> JSONResponse:
    tb = traceback.format_exc()
    exc_str = str(exc) or type(exc).__name__
    message = exc_str
    detail = {
        "exc_type": type(exc).__name__,
        "exc_str": exc_str,
        "traceback": tb,
    }
    _log_error(request=request, status_code=500, error_type=_ET_INTERNAL,
               message=message, traceback_text=tb, detail=detail)
    # Surface the REAL error details to the client in every environment
    # (including production) instead of a generic "internal server error".
    return _endpoint_json(500, message, "INTERNAL_ERROR", details=detail)


def register_error_handlers(app: FastAPI) -> None:
    """Install all global exception handlers onto the FastAPI app.

    More specific handlers (ApiError, RequestValidationError) take precedence;
    the catch-all ``Exception`` handler only catches genuinely unhandled 5xx.
    """
    app.add_exception_handler(ApiError, _handle_api_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_error)
    app.add_exception_handler(Exception, _handle_internal_error)