from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.rules.bands import derive_band  # noqa: E402


@pytest.fixture(scope="session")
def default_band():
    """The product-spec band: 90.50 +/- 8% = 83.26 .. 97.74."""
    return derive_band(90.50, 0.08)


@pytest.fixture(autouse=True)
def _hermetic_error_log_sink(monkeypatch):
    """Keep test-triggered errors out of the real ``error_logs`` table.

    The global handlers in ``core/errors.py`` persist every non-404/405 error via
    a best-effort ``get_db()`` insert. That ``get_db`` binding is separate from the
    router modules the tests already stub, so any 4xx/5xx a test exercises
    (validation 422s, rate-limit 429s, the deliberate settle RuntimeError, the
    invalid-state 400, etc.) would otherwise open a real DB connection and write
    test-fixture rows (e.g. ``TRIP-101``, state ``ZZ``) into the error dashboard.
    Neutralise the sink so the suite stays hermetic.
    """
    import backend.app.core.errors as errors

    @contextlib.contextmanager
    def _noop_db():
        yield mock.MagicMock()

    monkeypatch.setattr(errors, "get_db", _noop_db)
