"""Regression tests: social sign-up can never create a super_admin.

Requirement: users who sign up from the login screen (Google / Facebook) are
always `trip_manager`. `super_admin` only ever comes from the manual seed
script (```database/super_admin.sql```), and `driver` accounts are only created
by a `trip_manager`. These tests pin down that `create_or_link_social_user`
coerces the default role so a brand-new social account can never be elevated to
`super_admin` (and is never created as a `driver` through the self-signup path).
"""

from __future__ import annotations

from unittest import mock

from backend.app.db.queries.users import create_or_link_social_user


def _new_user_conn():
    """A conn whose cursor: provider lookup -> None, email lookup -> None,
    INSERT returns the new row id, then get_user_by_id returns the full row."""
    cur = mock.MagicMock()
    cur.fetchone.side_effect = [
        None,  # get_user_by_provider
        None,  # get_user_by_email
        {"id": 9},  # INSERT RETURNING id
        {"id": 9, "email": "self@signup.example", "role": "trip_manager",
         "full_name": "Self Signup", "is_active": True},  # get_user_by_id
    ]
    conn = mock.MagicMock()
    conn.cursor.return_value = cur
    return conn


def _insert_param(cur, pos):
    calls = [c.args for c in cur.execute.call_args_list if c.args and "INSERT INTO users" in c.args[0]]
    assert calls, "expected an INSERT for the new social user"
    return calls[0][1][pos]


def test_new_social_user_forced_to_trip_manager_when_default_is_super_admin():
    """Even if a misconfigured default_role is super_admin, the new user is trip_manager."""
    conn = _new_user_conn()
    cur = conn.cursor.return_value

    user, created = create_or_link_social_user(
        conn, "google", "sub-123", "self@signup.example", "Self Signup", "super_admin"
    )

    assert created is True
    assert _insert_param(cur, 3) == "trip_manager"


def test_new_social_user_never_created_as_driver():
    """The self-signup path cannot spawn a driver — drivers come from a manager."""
    conn = _new_user_conn()
    cur = conn.cursor.return_value

    create_or_link_social_user(conn, "google", "sub-2", "b@signup.example", "B", "driver")

    assert _insert_param(cur, 3) == "trip_manager"


def test_new_social_user_default_stays_trip_manager():
    """The normal default (trip_manager) is preserved on brand-new sign-up."""
    conn = _new_user_conn()
    cur = conn.cursor.return_value

    create_or_link_social_user(conn, "google", "sub-3", "c@signup.example", "C", "trip_manager")

    assert _insert_param(cur, 3) == "trip_manager"


def test_existing_social_account_keeps_role_and_links_no_insert():
    """A returning Google user (match on provider_sub) keeps their stored role."""
    stored = {"id": 4, "email": "return@signup.example", "role": "trip_manager",
              "full_name": "Return", "is_active": True}
    cur = mock.MagicMock()
    cur.fetchone.side_effect = [stored]
    conn = mock.MagicMock()
    conn.cursor.return_value = cur

    user, created = create_or_link_social_user(conn, "google", "sub-9", "return@signup.example", "X", "super_admin")

    assert created is False
    assert user["id"] == 4
    assert user["role"] == "trip_manager"
    sqls = [c.args[0] for c in cur.execute.call_args_list if c.args]
    assert not any("INSERT INTO users" in sql for sql in sqls)