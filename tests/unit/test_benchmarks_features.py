"""Rules & Rates page features: per-user favorites, the manager's usual
(house) operating state, and previous-price capture for the ▲/▼ Change column.

Covers:
* POST/DELETE /api/v1/benchmarks/{state_code}/favorite  -> favorites toggle
* PUT      /api/v1/benchmarks/home-state               -> usual-state setting
* GET      /api/v1/benchmarks                          -> payload carries both
* upsert_benchmarks_from_live                           -> preserves the old
  price in `previous_price` only when the price actually changed
"""

from __future__ import annotations

from unittest import mock

import pytest
from fastapi.testclient import TestClient

from backend.app.db.queries.benchmarks import upsert_benchmarks_from_live
from backend.app.main import app

MOCK_MANAGER = {"user_id": 7, "username": "mgr", "role": "trip_manager"}


def _make_db(cur):
    """Wrap a fake cursor in a connection + `with`-able db object."""
    conn = mock.MagicMock()
    conn.cursor.return_value = cur
    db_obj = mock.MagicMock()
    db_obj.__enter__ = mock.MagicMock(return_value=conn)
    db_obj.__exit__ = mock.MagicMock(return_value=False)
    return db_obj


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def resolve_db(monkeypatch):
    """Patch get_db + get_current_user inside the benchmarks router module."""
    def _patch(db_obj):
        monkeypatch.setattr(
            "backend.app.api.v1.benchmarks.get_db", lambda: db_obj
        )

    def _as_user(user):
        monkeypatch.setattr(
            "backend.app.api.v1.benchmarks.get_current_user",
            lambda request: user,
        )
        monkeypatch.setattr(
            "backend.app.core.security.get_current_user", lambda request: user
        )

    return _patch, _as_user


# ---- Unauthenticated guardrails ----------------------------------------------


def test_favorite_and_home_state_routes_require_auth(client):
    assert client.post("/api/v1/benchmarks/UP/favorite", json={}).status_code == 401
    assert client.delete("/api/v1/benchmarks/UP/favorite").status_code == 401
    assert (
        client.put("/api/v1/benchmarks/home-state", json={"state_code": "UP"}).status_code
        == 401
    )


# ---- Favorites ----------------------------------------------------------------


def test_add_favorite_uppercases_code_and_inserts(client, resolve_db):
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.post("/api/v1/benchmarks/up/favorite", json={})

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == {"state_code": "UP", "is_favorite": True}
    ins = [
        c for c in cur.execute.call_args_list
        if "INSERT INTO benchmark_favorites" in str(c.args[0])
    ]
    assert ins and ins[0].args[1] == (7, "UP"), ins


def test_add_favorite_rejects_unknown_state(client, resolve_db):
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.post("/api/v1/benchmarks/ZZ/favorite", json={})

    assert resp.status_code == 400, resp.text
    assert not any(
        "INSERT INTO benchmark_favorites" in str(c.args[0])
        for c in cur.execute.call_args_list
    )


def test_remove_favorite_deletes_row(client, resolve_db):
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.rowcount = 1
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.delete("/api/v1/benchmarks/UP/favorite")

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == {"state_code": "UP", "is_favorite": False}
    deletes = [
        c for c in cur.execute.call_args_list
        if "DELETE FROM benchmark_favorites" in str(c.args[0])
    ]
    assert deletes and deletes[0].args[1] == (7, "UP")


# ---- Usual (home) state -------------------------------------------------------


def test_set_home_state_validates_and_updates(client, resolve_db):
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.rowcount = 1
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.put("/api/v1/benchmarks/home-state", json={"state_code": "up"})

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == {"home_state_code": "UP"}
    ups = [
        c for c in cur.execute.call_args_list
        if "UPDATE users SET home_state_code" in str(c.args[0])
    ]
    assert ups and ups[0].args[1] == ("UP", 7), ups


def test_set_home_state_clears_on_empty_value(client, resolve_db):
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.rowcount = 1
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.put("/api/v1/benchmarks/home-state", json={"state_code": ""})

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == {"home_state_code": None}


# ---- GET payload ---------------------------------------------------------------


def test_get_benchmarks_returns_home_state_and_favorite_flags(client, resolve_db):
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.fetchall.return_value = [{"id": 1, "state_code": "UP", "is_favorite": True}]
    cur.fetchone.return_value = {"home_state_code": "UP"}
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.get("/api/v1/benchmarks")

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["home_state_code"] == "UP"
    assert data["benchmarks"][0]["is_favorite"] is True
    first_stmt = str(cur.execute.call_args_list[0].args[0])
    assert "benchmark_favorites" in first_stmt  # favorites join present


# ---- previous_price capture on live sync ----------------------------------------


def test_upsert_preserves_previous_price_on_price_change():
    cur = mock.MagicMock()
    cur.rowcount = 1
    conn = mock.MagicMock()
    conn.cursor.return_value = cur

    touched = upsert_benchmarks_from_live(
        conn,
        [
            {
                "state_code": "UP",
                "state_name": "Uttar Pradesh",
                "benchmark_price_per_liter": 91.5,
            }
        ],
    )

    assert touched == 1
    stmt = str(cur.execute.call_args_list[0].args[0])
    assert "previous_price = CASE" in stmt
    assert "IS DISTINCT FROM" in stmt
