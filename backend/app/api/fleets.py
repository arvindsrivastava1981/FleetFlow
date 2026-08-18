"""Fleets router — Super Admin CRUD for Fleet Owners / Subscription Management.

Super Admins can create, edit, activate/deactivate fleets. Each fleet
owns its subscription state (trial, plan, Razorpay refs, vehicle_limit).
Trip managers and drivers are linked via `users.fleet_id`.
"""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.app.core.security import esc, get_current_user, require_role
from backend.app.db.connection import get_db
from backend.app.db.queries.fleets import (
    deactivate_fleet,
    fleet_phone_exists,
    get_all_fleets,
    get_all_plans,
    get_fleet_by_id,
    insert_fleet,
    reactivate_fleet,
    update_fleet,
)
from backend.app.web.chrome import render_footer, render_header, render_sidebar

router = APIRouter()

_STATUS_CLS = {
    "TRIAL": "bg-sky-100 text-sky-800",
    "ACTIVE": "bg-emerald-100 text-emerald-800",
    "PAST_DUE": "bg-amber-100 text-amber-800",
    "CANCELLED": "bg-rose-100 text-rose-800",
    "EXPIRED": "bg-slate-100 text-slate-600",
}
def _fleet_row(f: dict) -> str:
    fid = f["id"]
    status_cls = _STATUS_CLS.get(f.get("subscription_status", ""), "bg-slate-100 text-slate-600")
    status_txt = (f.get("subscription_status") or "TRIAL").replace("_", " ").title()
    plan = esc(f.get("plan_name") or "\u2014")
    edit = f'<a href="/fleets/edit/{fid}" class="text-sky-600 hover:text-sky-800">Edit</a>'
    if f.get("is_active"):
        act = f'<a href="/fleets/deactivate/{fid}" onclick="return confirm(&quot;Deactivate?&quot;)" class="text-rose-600 hover:text-rose-800">Deactivate</a>'
    else:
        act = f'<a href="/fleets/activate/{fid}" class="text-emerald-600 hover:text-emerald-800">Activate</a>'
    return f"""<tr class="border-b border-slate-100 hover:bg-slate-50">
<td class="p-3 text-xs font-bold text-slate-800">{esc(f['owner_name'])}</td>
<td class="p-3 text-xs text-slate-600">{esc(f['phone'])}</td>
<td class="p-3 text-xs text-slate-600">{esc(f.get('email') or '\u2014')}</td>
<td class="p-3 text-xs">{plan}</td>
<td class="p-3 text-xs"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold {status_cls}">{status_txt}</span></td>
<td class="p-3 text-xs text-slate-600">{f.get('vehicle_count',0)} / {f.get('vehicle_limit',1)}</td>
<td class="p-3 text-xs flex gap-3">{edit}{act}</td></tr>"""
def _plan_opts(selected: str = "") -> str:
    with get_db() as conn:
        plans = get_all_plans(conn)
    opts = []
    for p in plans:
        if p["code"] == "TRIAL":
            continue
        sel = " selected" if p["code"] == selected else ""
        opts.append(f'<option value="{p["code"]}"{sel}>{p["name"]} (₹{p["price"]:,.0f})</option>')
    return "".join(opts)


def _fleet_form(user: dict, action: str, editing: dict | None = None) -> str:
    role = user.get("role", "super_admin")
    uname = user.get("username", "")
    if editing:
        owner_name = esc(editing["owner_name"])
        phone = esc(editing["phone"] or "")
        email = esc(editing.get("email") or "")
        sel = editing.get("subscription_plan", "MONTHLY")
        title = f"Edit Fleet: {editing['owner_name']}"
    else:
        owner_name = phone = email = ""
        sel = "MONTHLY"
        title = "Create New Fleet"
    plan_select = _plan_opts(sel)
    bid = editing["id"] if editing else ""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
<div class="max-w-2xl mx-auto space-y-6">
{render_header(authenticated=True, username=uname, role=role)}
<div class="flex flex-col lg:flex-row gap-4">
{render_sidebar("fleets", role)}
<main class="flex-1 space-y-4">
<div class="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-4">
<h2 class="text-lg font-extrabold">{title}</h2>
<form action="{action}" method="post" class="space-y-4 text-xs">
<input type="hidden" name="id" value="{bid}">
<div><label class="font-bold text-slate-700 block">Owner / Fleet Name</label>
<input type="text" name="owner_name" required value="{owner_name}" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
<div class="grid grid-cols-2 gap-4">
<div><label class="font-bold text-slate-700 block">Phone</label>
<input type="text" name="phone" required value="{phone}" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
<div><label class="font-bold text-slate-700 block">Email</label>
<input type="email" name="email" value="{email}" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
</div>
<div><label class="font-bold text-slate-700 block">Target Subscription Plan</label>
<select name="subscription_plan" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm">{plan_select}</select>
<p class="text-[10px] text-slate-400 mt-1">Every new fleet starts a 15-day free trial. This is the post-trial plan.</p>
</div>
<div class="flex gap-3">
<a href="/fleets" class="flex-1 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold py-2.5 rounded-xl">Cancel</a>
<button class="flex-1 bg-sky-600 hover:bg-sky-700 text-white font-bold py-2.5 rounded-xl">{'Save Changes' if editing else 'Create Fleet'}</button>
</div>
</form></div></main></div>
{render_footer()}</div></body></html>"""
@router.get("/fleets", response_class=HTMLResponse)
def list_fleets(request: Request):
    guard = require_role(request, "super_admin")
    if guard:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        fleets = get_all_fleets(conn)
    rows = "".join([_fleet_row(f) for f in fleets])
    empty = '<tr><td colspan="7" class="p-6 text-center text-xs text-slate-400">No fleets yet.</td></tr>'
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Manage Fleets</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
<div class="max-w-7xl mx-auto space-y-6">
{render_header(authenticated=True, username=user['username'], role=user['role'])}
<div class="flex flex-col lg:flex-row gap-4">
{render_sidebar("fleets", user['role'])}
<main class="flex-1 space-y-4">
<div class="flex justify-between">
<div><h2 class="text-lg font-extrabold">Manage Fleets</h2><p class="text-xs text-slate-500">Fleet owners, subscription status, and plan limits.</p></div>
<a href="/fleets/create" class="bg-sky-600 hover:bg-sky-700 text-white font-bold px-4 py-2.5 rounded-xl text-xs">Add Fleet</a>
</div>
<div class="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
<table class="w-full text-left">
<thead class="bg-slate-50 border-b"><tr>
<th class="p-3 text-[10px] font-bold text-slate-500">Owner</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Phone</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Email</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Plan</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Status</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Vehicles</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Action</th>
</tr></thead>
<tbody>{rows if fleets else empty}</tbody></table></div></main></div>
{render_footer()}</div></body></html>"""


@router.get("/fleets/create", response_class=HTMLResponse)
def create_fleet_form(request: Request):
    guard = require_role(request, "super_admin")
    if guard:
        return guard
    return _fleet_form(get_current_user(request), "/fleets/create", editing=None)


@router.post("/fleets/create")
def create_fleet_submit(
    request: Request,
    owner_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(None),
    subscription_plan: str = Form("MONTHLY"),
):
    guard = require_role(request, "super_admin")
    if guard:
        return guard
    p = phone.strip()
    if not p:
        return RedirectResponse(url="/fleets/create?error=phone", status_code=303)
    with get_db() as conn:
        if fleet_phone_exists(conn, p):
            return RedirectResponse(url="/fleets/create?error=dup", status_code=303)
        insert_fleet(conn, owner_name.strip(), p, email.strip() if email else None, subscription_plan)
    return RedirectResponse(url="/fleets", status_code=303)


@router.get("/fleets/edit/{id}", response_class=HTMLResponse)
def edit_fleet_form(request: Request, id: int):
    guard = require_role(request, "super_admin")
    if guard:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        existing = get_fleet_by_id(conn, id)
    if not existing:
        return RedirectResponse(url="/fleets", status_code=303)
    return _fleet_form(user, f"/fleets/edit/{id}", editing=existing)


@router.post("/fleets/edit/{id}")
def edit_fleet_submit(
    request: Request, id: int,
    owner_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(None),
    subscription_plan: str = Form("MONTHLY"),
):
    guard = require_role(request, "super_admin")
    if guard:
        return guard
    p = phone.strip()
    if not p:
        return RedirectResponse(url=f"/fleets/edit/{id}?error=phone", status_code=303)
    with get_db() as conn:
        if fleet_phone_exists(conn, p, exclude_id=id):
            return RedirectResponse(url=f"/fleets/edit/{id}?error=dup", status_code=303)
        update_fleet(conn, id, owner_name.strip(), p, email.strip() if email else None)
    return RedirectResponse(url="/fleets", status_code=303)


@router.get("/fleets/deactivate/{id}")
def deactivate_fleet_route(request: Request, id: int):
    guard = require_role(request, "super_admin")
    if guard:
        return guard
    with get_db() as conn:
        deactivate_fleet(conn, id)
    return RedirectResponse(url="/fleets", status_code=303)


@router.get("/fleets/activate/{id}")
def activate_fleet_route(request: Request, id: int):
    guard = require_role(request, "super_admin")
    if guard:
        return guard
    with get_db() as conn:
        reactivate_fleet(conn, id)
    return RedirectResponse(url="/fleets", status_code=303)
