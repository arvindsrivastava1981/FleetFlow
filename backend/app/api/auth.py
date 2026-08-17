"""Auth router — login/logout with per-user credentials.

Replaces the single hardcoded USER_PASSWORD login with username + password
validation against the `users` table. Brute-force defense (per-IP lockout)
and 72h session TTL are preserved from the security layer.
"""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.app.core.config import settings
from backend.app.core.security import (
    AUTH_COOKIE,
    clear_login_failures,
    create_session,
    destroy_session,
    get_current_user,
    login_allowed,
    register_login_failure,
)
from backend.app.db.connection import get_db
from backend.app.db.queries.users import get_user_by_username
from backend.app.core.password import verify_password
from backend.app.web.chrome import render_footer, render_header

router = APIRouter()


def _client_ip(request: Request) -> str:
    # Trust the X-Forwarded-For first value when behind a proxy; fall back to
    # the direct client. Production (Render) terminates TLS and sets this header.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, error: str | None = None) -> str:
    ip = _client_ip(request)
    allowed, _seconds = login_allowed(ip)
    return f"""<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VahanKhata Login</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-5xl mx-auto space-y-6">
            {render_header(authenticated=False)}
            <main class="min-h-[60vh] flex items-center justify-center">
            <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-8 w-full max-w-sm space-y-5">
            <div class="text-center space-y-1">
                <div class="bg-sky-500 inline-block p-2 rounded-xl text-white font-black text-xl">VK</div>
                <h1 class="text-lg font-extrabold text-slate-800">Login</h1>
                <p class="text-xs text-slate-500">Enter your username and password</p>
            </div>
            {'<p class="text-xs text-rose-600 font-semibold text-center">Incorrect username or password. Try again.</p>' if error == '1' else ''}
            {'<p class="text-xs text-rose-600 font-semibold text-center">Account is inactive. Contact your administrator.</p>' if error == 'inactive' else ''}
            {'<p class="text-xs text-rose-600 font-semibold text-center">Too many failed attempts. Try again later.</p>' if error == 'locked' else ''}
            <form action="/login" method="post" class="space-y-3">
                <input type="text" name="username" required autofocus placeholder="Username"
                       class="w-full text-sm border rounded-lg p-2.5 bg-slate-50 outline-none focus:ring-2 focus:ring-sky-400">
                <input type="password" name="password" required placeholder="Password"
                       class="w-full text-sm border rounded-lg p-2.5 bg-slate-50 outline-none focus:ring-2 focus:ring-sky-400">
                <button type="submit" class="w-full bg-sky-600 hover:bg-sky-500 text-white font-bold py-2.5 rounded-xl text-sm transition shadow">
                    Login
                </button>
            </form>
            </div>
            </main>
            {render_footer()}
        </div>
    </body>
    </html>"""


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    ip = _client_ip(request)
    allowed, _lock_remaining = login_allowed(ip)
    if not allowed:
        return RedirectResponse(url="/login?error=locked", status_code=303)

    with get_db() as conn:
        user = get_user_by_username(conn, username.strip())

    if user is None or not verify_password(password, user["password_hash"]):
        remaining = register_login_failure(ip)
        return RedirectResponse(url="/login?error=1", status_code=303)

    if not user["is_active"]:
        return RedirectResponse(url="/login?error=inactive", status_code=303)

    clear_login_failures(ip)
    token = create_session(user["id"], user["username"], user["role"])
    landing = {
        "super_admin": "/admin",
        "trip_manager": "/manager",
        "driver": "/driver",
    }.get(user["role"], "/dashboard")
    response = RedirectResponse(url=landing, status_code=303)
    response.set_cookie(
        key=AUTH_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
    )
    return response


@router.get("/logout")
def logout(request: Request):
    destroy_session(request)
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(AUTH_COOKIE)
    return response