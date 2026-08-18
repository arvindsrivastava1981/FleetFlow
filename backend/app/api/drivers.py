"""Drivers router Trip Manager CRUD for Driver users."""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.app.core.password import hash_password
from backend.app.core.security import esc, get_current_user, require_role
from backend.app.db.connection import get_db
from backend.app.db.queries.users import (
    create_user, deactivate_user, get_all_users, get_user_by_id, reactivate_user, update_user,
)
from backend.app.web.chrome import render_footer, render_header, render_sidebar

router = APIRouter()










@router.get("/drivers", response_class=HTMLResponse)
def list_drivers(request: Request):
    guard = require_role(request, "trip_manager", "super_admin")
    if guard:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        drivers = get_all_users(conn, role_filter="driver")
    rows = "".join([_driver_row(d) for d in drivers])
    empty = '<tr><td colspan="7" class="p-6 text-center text-xs text-slate-400">No drivers yet.</td></tr>'
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Manage Drivers</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
<div class="max-w-7xl mx-auto space-y-6">
{render_header(authenticated=True, username=user["username"], role=user["role"])}
<div class="flex flex-col lg:flex-row gap-4">
{render_sidebar("drivers", user["role"])}
<main class="flex-1 space-y-4">
<div class="flex justify-between">
<div><h2 class="text-lg font-extrabold">Manage Drivers</h2><p class="text-xs text-slate-500">Create and manage driver accounts.</p></div>
<a href="/drivers/create" class="bg-sky-600 hover:bg-sky-700 text-white font-bold px-4 py-2.5 rounded-xl text-xs">Add Driver</a>
</div>
<div class="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
<table class="w-full text-left">
<thead class="bg-slate-50 border-b"><tr>
<th class="p-3 text-[10px] font-bold text-slate-500">Username</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Full Name</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Phone</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Email</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Batta</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Status</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Action</th>
</tr></thead>
<tbody>{rows if drivers else empty}</tbody>
</table></div></main></div>
{render_footer()}</div></body></html>"""


def _driver_row(d: dict) -> str:
    uid = d["id"]
    edit_link = f'<a href="/drivers/edit/{uid}" class="text-sky-600 hover:text-sky-800">Edit</a>'
    if d["is_active"]:
        status_cls = "bg-emerald-100 text-emerald-800"
        status_txt = "Active"
        act_link = f'<a href="/drivers/deactivate/{uid}" onclick="return confirm(&quot;Deactivate?&quot;)" class="text-rose-600 hover:text-rose-800">Deactivate</a>'
    else:
        status_cls = "bg-rose-100 text-rose-800"
        status_txt = "Inactive"
        act_link = f'<a href="/drivers/activate/{uid}" class="text-emerald-600 hover:text-emerald-800">Activate</a>'
    batta_type = d.get("batta_type") or "FIXED_TRIP"
    batta_rate = d.get("default_batta_rate")
    batta_display = (
        "NONE" if batta_type == "NONE"
        else f"{batta_type} · ₹{batta_rate:,.2f}" if batta_rate is not None
        else batta_type
    )
    return f"""
        <tr class="border-b border-slate-100 hover:bg-slate-50">
            <td class="p-3 text-xs font-bold text-slate-800">{esc(d["username"])}</td>
            <td class="p-3 text-xs text-slate-600">{esc(d["full_name"])}</td>
            <td class="p-3 text-xs text-slate-600">{esc(d["phone"] or "")}</td>
            <td class="p-3 text-xs text-slate-600">{esc(d["email"] or "")}</td>
            <td class="p-3 text-xs text-slate-600">{esc(batta_display)}</td>
            <td class="p-3 text-xs"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold {status_cls}">{esc(status_txt)}</span></td>
            <td class="p-3 text-xs flex gap-3">{edit_link}{act_link}</td>
        </tr>"""


def _driver_form(user: dict, action: str, editing: dict | None = None) -> str:
    uname = esc(editing["username"]) if editing else ""
    fname = esc(editing["full_name"]) if editing else ""
    phone = esc(editing["phone"] or "") if editing else ""
    email = esc(editing["email"] or "") if editing else ""
    batta_type = (editing.get("batta_type") if editing else "") or "FIXED_TRIP"
    batta_rate = (editing.get("default_batta_rate") if editing else "") or "2500.00"
    batta_opts = "".join(
        f'<option value="{t}"{" selected" if t == batta_type else ""}>{t}</option>'
        for t in ("FIXED_TRIP", "PER_KM", "DAILY", "NONE")
    )
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Driver Form</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
<div class="max-w-2xl mx-auto space-y-6">
{render_header(authenticated=True, username=user["username"], role=user["role"])}
<h2 class="text-lg font-extrabold">{"Edit Driver" if editing else "Create New Driver"}</h2>
<div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
<form action="{action}" method="post" class="space-y-4">
<div><label class="text-xs font-bold text-slate-700">Username</label>
<input type="text" name="username" required value="{uname}" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
<div><label class="text-xs font-bold text-slate-700">Full Name</label>
<input type="text" name="full_name" required value="{fname}" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
<div><label class="text-xs font-bold text-slate-700">Phone</label>
<input type="text" name="phone" value="{phone}" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
<div><label class="text-xs font-bold text-slate-700">Email</label>
<input type="email" name="email" value="{email}" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
<div class="grid grid-cols-2 gap-3">
<div><label class="text-xs font-bold text-slate-700">Batta Type</label>
<select name="batta_type" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm">{batta_opts}</select></div>
<div><label class="text-xs font-bold text-slate-700">Batta Rate (₹ / trip)</label>
<input type="number" step="0.01" min="0" name="default_batta_rate" value="{batta_rate}" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
</div>
<p class="text-[10px] text-slate-400">FIXED_TRIP = flat ₹ per trip · PER_KM / DAILY reserved for future calculation · NONE = driver receives no batta.</p>
<div><label class="text-xs font-bold text-slate-700">Password (blank = keep current)</label>
<input type="password" name="password" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
<div class="flex gap-3"><a href="/drivers" class="flex-1 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold py-2.5 rounded-xl">Cancel</a>
<button class="flex-1 bg-sky-600 hover:bg-sky-700 text-white font-bold py-2.5 rounded-xl">Save</button></div>
</form></div></div>
</body></html>"""


@router.get("/drivers/create", response_class=HTMLResponse)
def create_driver_form(request: Request):
    guard = require_role(request, "trip_manager", "super_admin")
    if guard:
        return guard
    return _driver_form(get_current_user(request), "/drivers/create", editing=None)


@router.post("/drivers/create")
def create_driver_submit(
    request: Request,
    username: str = Form(...), full_name: str = Form(...),
    phone: str = Form(None), email: str = Form(None), password: str = Form(...),
    batta_type: str = Form("FIXED_TRIP"),
    default_batta_rate: float | str = Form("2500.00"),
):
    guard = require_role(request, "trip_manager", "super_admin")
    if guard:
        return guard
    if not password:
        return RedirectResponse(url="/drivers/create", status_code=303)
    user = get_current_user(request)
    with get_db() as conn:
        create_user(conn, username.strip(), hash_password(password), full_name.strip(),
                    "driver", phone.strip() if phone else None,
                    email.strip() if email else None,
                    created_by=user["user_id"],
                    batta_type=batta_type,
                    default_batta_rate=default_batta_rate)
    return RedirectResponse(url="/drivers", status_code=303)


@router.get("/drivers/edit/{id}")
def edit_driver_form(request: Request, id: int):
    guard = require_role(request, "trip_manager", "super_admin")
    if guard:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        existing = get_user_by_id(conn, id)
    if not existing:
        return RedirectResponse(url="/drivers", status_code=303)
    return _driver_form(user, f"/drivers/edit/{id}", editing=existing)


@router.post("/drivers/edit/{id}")
def edit_driver_submit(
    request: Request, id: int,
    username: str = Form(...), full_name: str = Form(...),
    phone: str = Form(None), email: str = Form(None), password: str = Form(None),
    batta_type: str = Form("FIXED_TRIP"),
    default_batta_rate: float | str = Form("2500.00"),
):
    guard = require_role(request, "trip_manager", "super_admin")
    if guard:
        return guard
    pw_hash = hash_password(password) if password else None
    with get_db() as conn:
        update_user(conn, id, full_name.strip(), "driver",
                    phone.strip() if phone else None,
                    email.strip() if email else None,
                    password_hash=pw_hash,
                    batta_type=batta_type,
                    default_batta_rate=default_batta_rate)
    return RedirectResponse(url="/drivers", status_code=303)


@router.get("/drivers/deactivate/{id}")
def deactivate_driver(request: Request, id: int):
    guard = require_role(request, "trip_manager", "super_admin")
    if guard:
        return guard
    with get_db() as conn:
        deactivate_user(conn, id)
    return RedirectResponse(url="/drivers", status_code=303)


@router.get("/drivers/activate/{id}")
def activate_driver(request: Request, id: int):
    guard = require_role(request, "trip_manager", "super_admin")
    if guard:
        return guard
    with get_db() as conn:
        reactivate_user(conn, id)
    return RedirectResponse(url="/drivers", status_code=303)
