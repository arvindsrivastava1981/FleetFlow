from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.rules.bands import derive_band  # noqa: E402


@pytest.fixture(scope="session")
def default_band():
    """The product-spec band: 90.50 +/- 8% = 83.26 .. 97.74."""
    return derive_band(90.50, 0.08)
