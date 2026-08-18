"""Users router — Super Admin CRUD for all users.

Super Admin can create/edit/deactivate/activate both Trip Managers and Drivers.
"""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.app.core.password import hash_password, verify_password
from backend.app.core.security import esc, get_current_user, require_auth, require_role
from backend.app.db.connection import get_db
from backend.app.db.queries.users import (
    create_user,
    deactivate_user,
    get_all_users,
    get_user_by_id,
    reactivate_user,
    update_user,
)
from backend.app.web.chrome import render_footer, render_header, render_sidebar

router = APIRouter()
VALID_ROLES = ("super_admin", "trip_manager", "driver")
_ROLE_COLORS = {
    "super_admin": "bg-purple-100 text-purple-800",
    "trip_manager": "bg-blue-100 text-blue-800",
    "driver": "bg-green-100 text-green-800",
}
_ROLE_LABELS = {
    "super_admin": "Super Admin",
    "trip_manager": "Trip Manager",
    "driver": "Driver",
}


def _role_opts(selected: str = "") -> str:
    """Render role <option> elements, flagging the currently selected role."""
    opts = []
    for role in VALID_ROLES:
        sel = " selected" if role == selected else ""
        label = _ROLE_LABELS.get(role, role)
        opts.append(f'<option value="{role}"{sel}>{label}</option>')
    return "".join(opts)



def _action_links(u: dict) -> str:
    uid = u["id"]
    edit = f'<a href="/users/edit/{uid}" class="text-sky-600 hover:text-sky-800">Edit</a>'
    if u["is_active"]:
        deact = f'<a href="/users/deactivate/{uid}" onclick="return confirm(&quot;Deactivate?&quot;)" class="text-rose-600 hover:text-rose-800">Deactivate</a>'
    else:
        deact = f'<a href="/users/activate/{uid}" class="text-emerald-600 hover:text-emerald-800">Activate</a>'
    return edit + deact


def _user_row(u: dict) -> str:
    role_cls = _ROLE_COLORS.get(u["role"], "bg-slate-100 text-slate-800")
    status_cls = "bg-emerald-100 text-emerald-800" if u["is_active"] else "bg-rose-100 text-rose-800"
    status_txt = "Active" if u["is_active"] else "Inactive"
    return f"""
        <tr class="border-b border-slate-100 hover:bg-slate-50">
            <td class="p-3 text-xs font-bold text-slate-800">{esc(u['username'])}</td>
            <td class="p-3 text-xs text-slate-600">{esc(u['full_name'])}</td>
            <td class="p-3 text-xs">
                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold {role_cls}">{esc(u['role'])}</span>
            </td>
            <td class="p-3 text-xs text-slate-600">{esc(u['phone'] or '')}</td>
            <td class="p-3 text-xs text-slate-600">{esc(u['email'] or '')}</td>
            <td class="p-3 text-xs flex gap-3">{_action_links(u)}</td>
        </tr>"""





def _user_form(user: dict, action: str, editing: dict | None = None) -> str:
    uname = esc(editing["username"]) if editing else ""
    fname = esc(editing["full_name"]) if editing else ""
    phone = esc(editing["phone"] or "") if editing else ""
    email = esc(editing["email"] or "") if editing else ""
    sel = editing["role"] if editing else ""
    title = "Edit User" if editing else "Create New User"
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{title}</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
<div class="max-w-2xl mx-auto space-y-6">
{render_header(authenticated=True, username=user['username'], role=user['role'])}
<h2 class="text-lg font-extrabold">{esc(title)}</h2>
<div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
<form action="{action}" method="post" class="space-y-4">
<div><label class="text-xs font-bold text-slate-700">Username</label>
<input type="text" name="username" required value="{uname}" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
<div><label class="text-xs font-bold text-slate-700">Full Name</label>
<input type="text" name="full_name" required value="{fname}" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
<div><label class="text-xs font-bold text-slate-700">Role</label>
<select name="role" required class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm">{_role_opts(sel)}</select></div>
<div><label class="text-xs font-bold text-slate-700">Phone</label>
<input type="text" name="phone" value="{phone}" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
<div><label class="text-xs font-bold text-slate-700">Email</label>
<input type="email" name="email" value="{email}" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
<div><label class="text-xs font-bold text-slate-700">Password (blank = keep current)</label>
<input type="password" name="password" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
<div class="flex gap-3"><a href="/users" class="flex-1 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold py-2.5 rounded-xl">Cancel</a>
<button class="flex-1 bg-sky-600 hover:bg-sky-700 text-white font-bold py-2.5 rounded-xl">Save</button></div>
</form></div></div>
</body></html>"""


@router.get("/users", response_class=HTMLResponse)
def list_users(request: Request):
    guard = require_role(request, "super_admin")
    if guard:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        users = get_all_users(conn)
    rows = "".join([_user_row(u) for u in users])
    empty = '<tr><td colspan="6" class="p-6 text-center text-xs text-slate-400">No users yet.</td></tr>'
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Manage Users</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
<div class="max-w-7xl mx-auto space-y-6">
{render_header(authenticated=True, username=user['username'], role=user['role'])}
<div class="flex flex-col lg:flex-row gap-4">
{render_sidebar("users", user['role'])}
<main class="flex-1 space-y-4">
<div class="flex justify-between">
<div><h2 class="text-lg font-extrabold">Manage Users</h2><p class="text-xs text-slate-500">Create, edit, activate/deactivate managers and drivers.</p></div>
<a href="/users/create" class="bg-sky-600 hover:bg-sky-700 text-white font-bold px-4 py-2.5 rounded-xl text-xs">Add User</a>
</div>
<div class="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
<table class="w-full text-left">
<thead class="bg-slate-50 border-b"><tr>
<th class="p-3 text-[10px] font-bold text-slate-500">Username</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Name</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Role</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Phone</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Email</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Action</th>
</tr></thead>
<tbody>{rows if users else empty}</tbody>
</table></div></main></div>
{render_footer()}</div></body></html>"""


@router.get("/users/create", response_class=HTMLResponse)
def create_user_form(request: Request):
    guard = require_role(request, "super_admin")
    if guard:
        return guard
    return _user_form(get_current_user(request), "/users/create", editing=None)


@router.post("/users/create")
def create_user_submit(
    request: Request,
    username: str = Form(...), full_name: str = Form(...), role: str = Form(...),
    phone: str = Form(None), email: str = Form(None), password: str = Form(...),
):
    guard = require_role(request, "super_admin")
    if guard:
        return guard
    if role not in VALID_ROLES or not password:
        return RedirectResponse(url="/users/create", status_code=303)
    with get_db() as conn:
        create_user(conn, username.strip(), hash_password(password), full_name.strip(),
                    role, phone.strip() if phone else None,
                    email.strip() if email else None,
                    created_by=get_current_user(request)["user_id"])
    return RedirectResponse(url="/users", status_code=303)


@router.get("/users/edit/{id}")
def edit_user_form(request: Request, id: int):
    guard = require_role(request, "super_admin")
    if guard:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        existing = get_user_by_id(conn, id)
    if not existing:
        return RedirectResponse(url="/users", status_code=303)
    return _user_form(user, f"/users/edit/{id}", editing=existing)


@router.post("/users/edit/{id}")
def edit_user_submit(
    request: Request, id: int,
    username: str = Form(...), full_name: str = Form(...), role: str = Form(...),
    phone: str = Form(None), email: str = Form(None), password: str = Form(None),
):
    guard = require_role(request, "super_admin")
    if guard:
        return guard
    if role not in VALID_ROLES:
        return RedirectResponse(url=f"/users/edit/{id}", status_code=303)
    pw_hash = hash_password(password) if password else None
    with get_db() as conn:
        update_user(conn, id, full_name.strip(), role,
                    phone.strip() if phone else None,
                    email.strip() if email else None,
                    password_hash=pw_hash)
    return RedirectResponse(url="/users", status_code=303)


@router.get("/users/deactivate/{id}")
def deactivate_user_route(request: Request, id: int):
    guard = require_role(request, "super_admin")
    if guard:
        return guard
    with get_db() as conn:
        deactivate_user(conn, id)
    return RedirectResponse(url="/users", status_code=303)


@router.get("/users/activate/{id}")
def activate_user_route(request: Request, id: int):
    guard = require_role(request, "super_admin")
    if guard:
        return guard
    with get_db() as conn:
        reactivate_user(conn, id)
    return RedirectResponse(url="/users", status_code=303)


@router.get("/users/change-password", response_class=HTMLResponse)
def change_password_form(request: Request):
    """Show password change form for logged-in user."""
    guard = require_auth(request)
    if guard:
        return guard
    
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Change Password</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
<div class="max-w-md mx-auto space-y-6">
{render_header(authenticated=True, username=user['username'], role=user['role'])}
<h2 class="text-lg font-extrabold">Change Password</h2>
<div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
<form method="post" class="space-y-4">
<div><label class="text-xs font-bold text-slate-700">Current Password</label>
<input type="password" name="current_password" required class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
<div><label class="text-xs font-bold text-slate-700">New Password</label>
<input type="password" name="new_password" required class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm" minlength="4" placeholder="At least 4 characters"></div>
<div><label class="text-xs font-bold text-slate-700">Confirm New Password</label>
<input type="password" name="confirm_password" required class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm" minlength="4"></div>
<div class="flex gap-3">
<a href="/users" class="flex-1 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold py-2.5 rounded-xl">Cancel</a>
<button type="submit" class="flex-1 bg-sky-600 hover:bg-sky-700 text-white font-bold py-2.5 rounded-xl">Change Password</button>
</div>
</form></div></div>
</body></html>"""


@router.post("/users/change-password")
def change_password_submit(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
):
    """Change password - only for the logged-in user."""
    guard = require_auth(request)
    if guard:
        return guard
    
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    with get_db() as conn:
        db_user = get_user_by_id(conn, user["user_id"])
    
    if not db_user:
        return RedirectResponse(url="/users?error=user_not_found", status_code=303)
    
    # Verify current password
    if not verify_password(current_password, db_user["password_hash"]):
        return RedirectResponse(url="/users?error=wrong_password", status_code=303)
    
    # Validate new password
    if not new_password or len(new_password) < 4:
        return RedirectResponse(url="/users?error=weak_password", status_code=303)
    
    if new_password != confirm_password:
        return RedirectResponse(url="/users?error=password_mismatch", status_code=303)
    
    # Hash and update
    new_hash = hash_password(new_password)
    with get_db() as conn:
        update_user(conn, user["user_id"], db_user["full_name"], db_user["role"],
                    db_user["phone"], db_user["email"],
                    password_hash=new_hash)
    
    return RedirectResponse(url="/users?password_changed=1", status_code=303)


