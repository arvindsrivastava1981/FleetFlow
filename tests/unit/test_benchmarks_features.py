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
    """Patch get_db + get_current_user inside the benchmarks/states routers."""
    def _patch(db_obj):
        for _module in (
            "backend.app.api.v1.benchmarks",
            "backend.app.api.v1.states",
        ):
            monkeypatch.setattr(f"{_module}.get_db", lambda: db_obj)

    def _as_user(user):
        for _module in (
            "backend.app.api.v1.benchmarks",
            "backend.app.api.v1.states",
            "backend.app.core.security",
        ):
            monkeypatch.setattr(
                f"{_module}.get_current_user", lambda request: user
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


# ---- GET /states carries the caller's favorites --------------------------------


def test_list_states_flags_caller_favorites(client, resolve_db):
    """`GET /states` tags each state with the caller's favorite flag so driver
    dropdowns can pin starred states to the top."""
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.fetchall.return_value = [{"state_code": "UP"}]
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.get("/api/v1/states")

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    up = next(s for s in data if s["code"] == "UP")
    other = next(s for s in data if s["code"] != "UP")
    assert up["is_favorite"] is True
    assert other["is_favorite"] is False


# ---- GET /states?source=benchmarks reads the DB-backed picker list --------------


def test_list_states_benchmark_source_reads_db(client, resolve_db):
    """`?source=benchmarks` returns ONLY the states priced in `fuel_benchmarks`,
    each tagged with the caller's favorite flag — the fueling-state picker must
    never offer a state the rules engine cannot price."""
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.fetchall.return_value = [
        {"state_code": "MH", "state_name": "Maharashtra", "is_favorite": True},
        {"state_code": "UP", "state_name": "Uttar Pradesh", "is_favorite": False},
    ]
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.get("/api/v1/states?source=benchmarks")

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert [(s["code"], s["name"], s["is_favorite"]) for s in data] == [
        ("MH", "Maharashtra", True),
        ("UP", "Uttar Pradesh", False),
    ]
    stmt = str(cur.execute.call_args_list[0].args[0])
    assert "FROM fuel_benchmarks" in stmt
    assert "benchmark_favorites" in stmt


def test_list_states_benchmark_source_empty_table_falls_back_to_up(client, resolve_db):
    """With no rows in `fuel_benchmarks` yet, the picker degrades to UP alone."""
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.fetchall.return_value = []
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.get("/api/v1/states?source=benchmarks")

    assert resp.status_code == 200, resp.text
    assert resp.json()["data"] == [
        {"code": "UP", "name": "Uttar Pradesh", "is_favorite": False}
    ]


# ---- Regression: driver dashboard GroupingError masked as "no active trip" -----


def test_approved_cash_net_binds_trip_code_without_outer_column():
    """`approved_cash_net` must reference the trip via a bound parameter.

    The old SQL correlated the EXISTS subquery with the ungrouped outer
    ``expenses.trip_code`` -> psycopg2 GroupingError -> dashboard/overview 500
    for every driver WITH an active trip, which the WhatsApp view then reported
    as "You have no active trip right now."
    """
    from backend.app.db.queries.dashboards import approved_cash_net

    cur = mock.MagicMock()
    cur.fetchone.return_value = {"net": -120.5}
    conn = mock.MagicMock()
    conn.cursor.return_value = cur

    result = approved_cash_net(conn, "4191-2")

    assert result == -120.5
    stmt = str(cur.execute.call_args_list[0].args[0])
    assert "x.trip_code = expenses.trip_code" not in stmt
    assert cur.execute.call_args_list[0].args[1] == ("4191-2", "4191-2")


# ---- Live-rate sync is open to trip_manager + super_admin ----------------------


def test_sync_live_allows_trip_manager(client, resolve_db, monkeypatch):
    """`POST /benchmarks/sync-live` accepts trip_manager (not just super_admin)."""
    import backend.app.api.v1.benchmarks as benchmarks_mod

    monkeypatch.setattr(
        benchmarks_mod,
        "get_live_prices",
        lambda: [
            {
                "state_code": "UP",
                "state_name": "Uttar Pradesh",
                "benchmark_price_per_liter": 91.5,
            }
        ],
    )
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    cur.rowcount = 1
    patch_db(_make_db(cur))
    as_user(MOCK_MANAGER)

    resp = client.post("/api/v1/benchmarks/sync-live", json={})

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["updated"] == 1
    assert "UP" in data["states"]


def test_sync_live_forbidden_for_driver(client, resolve_db):
    """Drivers still get 403 — the guard allows only manager/admin roles."""
    patch_db, as_user = resolve_db
    cur = mock.MagicMock()
    patch_db(_make_db(cur))
    as_user({"user_id": 9, "username": "drv", "role": "driver"})

    resp = client.post("/api/v1/benchmarks/sync-live", json={})

    assert resp.status_code == 403
    assert not any(
        "INSERT INTO fuel_benchmarks" in str(c.args[0])
        for c in cur.execute.call_args_list
    )
