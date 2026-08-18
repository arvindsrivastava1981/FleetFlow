"""Vehicles router — Vehicle CRUD for Trip Managers & Super Admins.

Allows a trip_manager (or super_admin) to create, edit, activate/deactivate the
vehicles in their fleet. Vehicles are role-scoped: super_admin sees all,
trip_manager sees only the vehicles they created. The registered vehicles are
also the source for the Vehicle Number dropdown in the Start-Trip form.
"""
from __future__ import annotations

import re

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.app.core.config import settings
from backend.app.core.security import esc, get_current_user, require_role
from backend.app.db.connection import get_db
from backend.app.db.queries.fleets import (
    count_active_vehicles,
    get_default_fleet,
    get_fleet_entitlement,
    is_trial_active,
)
from backend.app.db.queries.users import get_user_fleet_id
from backend.app.db.queries.vehicles import (
    deactivate_vehicle,
    get_all_vehicles,
    get_vehicle_by_id,
    insert_vehicle,
    reactivate_vehicle,
    update_vehicle,
    vehicle_number_exists,
)
from backend.app.web.chrome import render_footer, render_header, render_sidebar

router = APIRouter()

PLATE_RE = re.compile(settings.plate_regex)


def _vehicle_row(v: dict) -> str:
    vid = v["id"]
    edit_link = f'<a href="/vehicles/edit/{vid}" class="text-sky-600 hover:text-sky-800">Edit</a>'
    if v["is_active"]:
        status_cls = "bg-emerald-100 text-emerald-800"
        status_txt = "Active"
        act_link = (
            f'<a href="/vehicles/deactivate/{vid}" onclick="return confirm(&quot;Deactivate this vehicle?&quot;)" '
            f'class="text-rose-600 hover:text-rose-800">Deactivate</a>'
        )
    else:
        status_cls = "bg-rose-100 text-rose-800"
        status_txt = "Inactive"
        act_link = (
            f'<a href="/vehicles/activate/{vid}" '
            f'class="text-emerald-600 hover:text-emerald-800">Activate</a>'
        )
    return f"""
        <tr class="border-b border-slate-100 hover:bg-slate-50">
            <td class="p-3 text-xs font-bold text-slate-800">{esc(v['vehicle_number'])}</td>
            <td class="p-3 text-xs text-slate-600">{esc(v['make_model'] or '—')}</td>
            <td class="p-3 text-xs text-slate-600">{esc(v['fleet_owner'] or '—')}</td>
            <td class="p-3 text-xs text-slate-600">{v['tank_capacity_liters']:,.0f} L</td>
            <td class="p-3 text-xs text-slate-600">{v['expected_km_per_liter']:,.2f} km/L</td>
            <td class="p-3 text-xs text-slate-600">{esc(v['owner_phone'] or '—')}</td>
            <td class="p-3 text-xs"><span class="px-2 py-0.5 rounded-full text-[10px] font-bold {status_cls}">{status_txt}</span></td>
            <td class="p-3 text-xs flex gap-3">
                {edit_link}
                {act_link}
            </td>
        </tr>"""


@router.get("/vehicles", response_class=HTMLResponse)
def list_vehicles(request: Request):
    guard = require_role(request, "trip_manager", "super_admin")
    if guard:
        return guard
    user = get_current_user(request)
    role = user["role"]
    user_id = user.get("user_id")
    with get_db() as conn:
        vehicles = get_all_vehicles(conn, role=role, user_id=user_id)
    rows = "".join([_vehicle_row(v) for v in vehicles])
    empty = '<tr><td colspan="8" class="p-6 text-center text-xs text-slate-400">No vehicles registered yet. Add one below.</td></tr>'
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Manage Vehicles</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
<div class="max-w-7xl mx-auto space-y-6">
{render_header(authenticated=True, username=user["username"], role=user["role"])}
<div class="flex flex-col lg:flex-row gap-4">
{render_sidebar("vehicles", user["role"])}
<main class="flex-1 space-y-4">
<div class="flex justify-between">
<div><h2 class="text-lg font-extrabold">Manage Vehicles</h2><p class="text-xs text-slate-500">Register the vehicles used by your drivers.</p></div>
<a href="/vehicles/create" class="bg-sky-600 hover:bg-sky-700 text-white font-bold px-4 py-2.5 rounded-xl text-xs">Add Vehicle</a>
</div>
<div class="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
<table class="w-full text-left">
<thead class="bg-slate-50 border-b"><tr>
<th class="p-3 text-[10px] font-bold text-slate-500">Vehicle Number</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Make / Model</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Fleet</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Tank Capacity</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Expected km/L</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Owner Phone</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Status</th>
<th class="p-3 text-[10px] font-bold text-slate-500">Action</th>
</tr></thead>
<tbody>{rows if vehicles else empty}</tbody>
</table></div></main></div>
{render_footer()}</div></body></html>"""
def _vehicle_form(user: dict, action: str, editing: dict | None = None) -> str:
    if editing:
        vehicle_number = esc(editing["vehicle_number"])
        make_model = esc(editing["make_model"] or "")
        tank_capacity_liters = editing["tank_capacity_liters"]
        expected_km_per_liter = editing["expected_km_per_liter"]
        owner_phone = esc(editing["owner_phone"] or "")
        title = f"Edit Vehicle: {editing['vehicle_number']}"
    else:
        vehicle_number = make_model = owner_phone = ""
        tank_capacity_liters = 350.00
        expected_km_per_liter = 4.00
        title = "Add Vehicle"
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{title}</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
<div class="max-w-2xl mx-auto space-y-6">
{render_header(authenticated=True, username=user["username"], role=user["role"])}
<div class="flex flex-col lg:flex-row gap-4">
{render_sidebar("vehicles", user["role"])}
<main class="flex-1 space-y-4">
<div class="bg-white border border-slate-200 rounded-2xl shadow-sm p-6 space-y-4">
<h2 class="text-lg font-extrabold">{title}</h2>
<form action="{action}" method="post" class="space-y-4 text-xs">
<input type="hidden" name="id" value="{editing['id'] if editing else ''}">
<div class="grid grid-cols-2 gap-4">
<div><label class="font-bold text-slate-700 block">Vehicle Number</label>
<input type="text" name="vehicle_number" required value="{vehicle_number}" placeholder="e.g. UP-93-AT-1234" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
<div><label class="font-bold text-slate-700 block">Make / Model</label>
<input type="text" name="make_model" value="{make_model}" placeholder="e.g. Tata 1613" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
</div>
<div class="grid grid-cols-2 gap-4">
<div><label class="font-bold text-slate-700 block">Tank Capacity (L)</label>
<input type="number" step="0.01" name="tank_capacity_liters" required value="{tank_capacity_liters}" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
<div><label class="font-bold text-slate-700 block">Expected km/L</label>
<input type="number" step="0.01" name="expected_km_per_liter" required value="{expected_km_per_liter}" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
</div>
<div><label class="font-bold text-slate-700 block">Owner Phone</label>
<input type="text" name="owner_phone" value="{owner_phone}" placeholder="Enter registered owner mobile" class="w-full border rounded-lg p-2.5 bg-slate-50 text-sm"></div>
<div class="flex gap-3">
<a href="/vehicles" class="flex-1 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold py-2.5 rounded-xl">Cancel</a>
<button class="flex-1 bg-sky-600 hover:bg-sky-700 text-white font-bold py-2.5 rounded-xl">{'Save Changes' if editing else '➕ Add Vehicle'}</button>
</div>
</form></div>
</main></div>
{render_footer()}</div></body></html>"""
@router.get("/vehicles/create", response_class=HTMLResponse)
def create_vehicle_form(request: Request):
    guard = require_role(request, "trip_manager", "super_admin")
    if guard:
        return guard
    return _vehicle_form(get_current_user(request), "/vehicles/create", editing=None)


@router.post("/vehicles/create")
def create_vehicle_submit(
    request: Request,
    vehicle_number: str = Form(...),
    make_model: str = Form(""),
    tank_capacity_liters: float = Form(350.0),
    expected_km_per_liter: float = Form(4.0),
    owner_phone: str = Form(""),
):
    guard = require_role(request, "trip_manager", "super_admin")
    if guard:
        return guard
    number = vehicle_number.strip().upper()
    if not PLATE_RE.match(number):
        return RedirectResponse(url="/vehicles/create?error=plate", status_code=303)
    user = get_current_user(request)
    user_id = user.get("user_id")
    with get_db() as conn:
        if vehicle_number_exists(conn, number):
            return RedirectResponse(url="/vehicles/create?error=dup", status_code=303)

        # Resolve which fleet this vehicle belongs to.
        fleet_id = get_user_fleet_id(conn, user_id) if user_id else None
        if fleet_id is None:
            default = get_default_fleet(conn)
            if default:
                fleet_id = default["id"]
        if fleet_id is None:
            return RedirectResponse(url="/vehicles/create?error=no_fleet", status_code=303)

        # Subscription gate: entitlement + vehicle limit.
        entitlement = get_fleet_entitlement(conn, fleet_id)
        if not entitlement or entitlement["subscription_status"] != "ACTIVE":
            # Free 15-day trial counts as active while it hasn't lapsed.
            if not (entitlement and is_trial_active(conn, fleet_id)):
                return RedirectResponse(url="/billing/upgrade", status_code=303)
        if count_active_vehicles(conn, fleet_id) >= entitlement["vehicle_limit"]:
            # Hit the cap -> single-vehicle subscription purchase.
            return RedirectResponse(url="/billing/vehicle-slot", status_code=303)

        insert_vehicle(
            conn, number, make_model.strip() or None,
            tank_capacity_liters, expected_km_per_liter,
            owner_phone.strip() or None, created_by=user_id, fleet_id=fleet_id,
        )
    return RedirectResponse(url="/vehicles", status_code=303)


@router.get("/vehicles/edit/{id}", response_class=HTMLResponse)
def edit_vehicle_form(request: Request, id: int):
    guard = require_role(request, "trip_manager", "super_admin")
    if guard:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        existing = get_vehicle_by_id(conn, id, role=user["role"], user_id=user.get("user_id"))
    if not existing:
        return RedirectResponse(url="/vehicles", status_code=303)
    return _vehicle_form(user, f"/vehicles/edit/{id}", editing=existing)


@router.post("/vehicles/edit/{id}")
def edit_vehicle_submit(
    request: Request, id: int,
    vehicle_number: str = Form(...),
    make_model: str = Form(""),
    tank_capacity_liters: float = Form(350.0),
    expected_km_per_liter: float = Form(4.0),
    owner_phone: str = Form(""),
):
    guard = require_role(request, "trip_manager", "super_admin")
    if guard:
        return guard
    number = vehicle_number.strip().upper()
    if not PLATE_RE.match(number):
        return RedirectResponse(url=f"/vehicles/edit/{id}?error=plate", status_code=303)
    with get_db() as conn:
        if vehicle_number_exists(conn, number, exclude_id=id):
            return RedirectResponse(url=f"/vehicles/edit/{id}?error=dup", status_code=303)
        update_vehicle(conn, id, number, make_model.strip() or None,
                       tank_capacity_liters, expected_km_per_liter,
                       owner_phone.strip() or None)
    return RedirectResponse(url="/vehicles", status_code=303)


@router.get("/vehicles/deactivate/{id}")
def deactivate_vehicle_route(request: Request, id: int):
    guard = require_role(request, "trip_manager", "super_admin")
    if guard:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        existing = get_vehicle_by_id(conn, id, role=user["role"], user_id=user.get("user_id"))
        if not existing:
            return RedirectResponse(url="/vehicles", status_code=303)
        deactivate_vehicle(conn, id)
    return RedirectResponse(url="/vehicles", status_code=303)


@router.get("/vehicles/activate/{id}")
def activate_vehicle_route(request: Request, id: int):
    guard = require_role(request, "trip_manager", "super_admin")
    if guard:
        return guard
    user = get_current_user(request)
    with get_db() as conn:
        existing = get_vehicle_by_id(conn, id, role=user["role"], user_id=user.get("user_id"))
        if not existing:
            return RedirectResponse(url="/vehicles", status_code=303)
        reactivate_vehicle(conn, id)
    return RedirectResponse(url="/vehicles", status_code=303)
