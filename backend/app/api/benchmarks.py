"""Fuel benchmarks router — CRUD page for per-state fuel price references.

Migrated from `fleetflow_interactive_demo.py`'s `/fuel-benchmarks` page/actions.
Security:
- §2.1 unauthenticated access -> `require_auth` 303-redirects to /login.
- §2.3 stored-XSS -> every DB-sourced value rendered via `security.esc()`.
"""
from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from backend.app.core.security import esc, get_current_user, require_auth
from backend.app.db.connection import get_db
from backend.app.db.queries.benchmarks import (
    delete_benchmark,
    get_all_benchmarks,
    get_benchmark_by_id,
    insert_benchmark,
    update_benchmark,
)
from backend.app.web.chrome import render_footer, render_header, render_sidebar

router = APIRouter()


@router.get("/fuel-benchmarks", response_class=HTMLResponse)
def fuel_benchmarks_page(request: Request, edit_id: int | None = None):
    guard = require_auth(request)
    if guard is not None:
        return guard

    with get_db() as conn:
        benchmarks = get_all_benchmarks(conn)
        editing = get_benchmark_by_id(conn, edit_id) if edit_id else None

    rows_html = "".join([f"""
        <tr class="border-b border-slate-100 hover:bg-slate-50">
            <td class="p-3 text-xs font-bold text-slate-800">{esc(b['state_code'])}</td>
            <td class="p-3 text-xs text-slate-600">{esc(b['state_name'])}</td>
            <td class="p-3 text-xs text-slate-600">₹{b['benchmark_price_per_liter']:,.2f}</td>
            <td class="p-3 text-xs text-slate-600">{b['tolerance_pct']}%</td>
            <td class="p-3 text-xs text-slate-400">{esc(b['effective_date'])}</td>
            <td class="p-3 text-xs flex gap-3">
                <a href="/fuel-benchmarks?edit_id={b['id']}" class="text-sky-600 hover:text-sky-800 font-semibold">Edit</a>
                <a href="/fuel-benchmarks/delete?id={b['id']}" onclick="return confirm('Delete this benchmark?')" class="text-rose-600 hover:text-rose-800 font-semibold">Delete</a>
            </td>
        </tr>""" for b in benchmarks])

    form_action = "/fuel-benchmarks/edit" if editing else "/fuel-benchmarks/add"
    form_title = f"Edit Benchmark: {esc(editing['state_name'])}" if editing else "Add New Benchmark"
    id_field = f'<input type="hidden" name="id" value="{editing["id"]}">' if editing else ''
    cancel_link = '<a href="/fuel-benchmarks" class="text-xs text-slate-400 hover:text-slate-600 ml-2">Cancel edit</a>' if editing else ''

    user = get_current_user(request) or {}
    return f"""<!DOCTYPE html>
    <html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>VahanKhata Fuel Benchmarks</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-7xl mx-auto space-y-6">
            {render_header(authenticated=True, username=user.get('username', ''), role=user.get('role', ''))}
            <div class="flex flex-col lg:flex-row gap-4">
                {render_sidebar("fuel-benchmarks")}
                <main class="flex-1 space-y-4">
                    <div>
                        <h2 class="text-lg font-extrabold text-slate-900">Fuel Benchmarks</h2>
                        <p class="text-xs text-slate-500">State-wise diesel price references used by the rules engine's price-band check.</p>
                    </div>
                    <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
                        <h3 class="text-sm font-extrabold text-slate-800 mb-3">{form_title}{cancel_link}</h3>
                        <form action="{form_action}" method="post" class="grid grid-cols-2 md:grid-cols-5 gap-3 items-end">
                            {id_field}
                            <div>
                                <label class="text-[11px] font-semibold text-slate-500 block mb-1">State Code</label>
                                <input name="state_code" required maxlength="10" value="{esc(editing['state_code']) if editing else ''}" placeholder="UP" class="w-full text-sm border rounded-lg p-2 bg-slate-50 outline-none focus:ring-2 focus:ring-sky-400">
                            </div>
                            <div>
                                <label class="text-[11px] font-semibold text-slate-500 block mb-1">State Name</label>
                                <input name="state_name" required maxlength="50" value="{esc(editing['state_name']) if editing else ''}" placeholder="Uttar Pradesh" class="w-full text-sm border rounded-lg p-2 bg-slate-50 outline-none focus:ring-2 focus:ring-sky-400">
                            </div>
                            <div>
                                <label class="text-[11px] font-semibold text-slate-500 block mb-1">Price ₹/L</label>
                                <input name="benchmark_price_per_liter" type="number" step="0.01" required value="{editing['benchmark_price_per_liter'] if editing else ''}" placeholder="90.50" class="w-full text-sm border rounded-lg p-2 bg-slate-50 outline-none focus:ring-2 focus:ring-sky-400">
                            </div>
                            <div>
                                <label class="text-[11px] font-semibold text-slate-500 block mb-1">Tolerance %</label>
                                <input name="tolerance_pct" type="number" step="0.01" value="{editing['tolerance_pct'] if editing else '8.0'}" placeholder="8.0" class="w-full text-sm border rounded-lg p-2 bg-slate-50 outline-none focus:ring-2 focus:ring-sky-400">
                            </div>
                            <div>
                                <label class="text-[11px] font-semibold text-slate-500 block mb-1">Effective Date</label>
                                <input name="effective_date" type="date" value="{editing['effective_date'] if editing else ''}" class="w-full text-sm border rounded-lg p-2 bg-slate-50 outline-none focus:ring-2 focus:ring-sky-400">
                            </div>
                            <button type="submit" class="bg-sky-600 hover:bg-sky-500 text-white font-bold px-4 py-2 rounded-xl text-sm transition shadow col-span-2 md:col-span-1">
                                {'Save Changes' if editing else '➕ Add Benchmark'}
                            </button>
                        </form>
                    </div>
                    <div class="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
                        <table class="w-full text-left">
                            <thead class="bg-slate-50 border-b border-slate-200">
                                <tr>
                                    <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Code</th>
                                    <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">State</th>
                                    <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Benchmark Price</th>
                                    <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Tolerance</th>
                                    <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Effective Date</th>
                                    <th class="p-3 text-[10px] font-bold text-slate-500 uppercase">Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rows_html if benchmarks else '<tr><td colspan="6" class="p-6 text-center text-xs text-slate-400">No fuel benchmarks yet.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </main>
            </div>
            {render_footer()}
        </div>
    </body></html>"""


@router.post("/fuel-benchmarks/add")
def fuel_benchmarks_add(
    request: Request,
    state_code: str = Form(...),
    state_name: str = Form(...),
    benchmark_price_per_liter: float = Form(...),
    tolerance_pct: float = Form(8.0),
    effective_date: str | None = Form(None),
):
    guard = require_auth(request)
    if guard is not None:
        return guard

    with get_db() as conn:
        insert_benchmark(
            conn,
            state_code.strip().upper(),
            state_name.strip(),
            benchmark_price_per_liter,
            tolerance_pct,
            effective_date or None,
        )
    return RedirectResponse(url="/fuel-benchmarks", status_code=303)


@router.post("/fuel-benchmarks/edit")
def fuel_benchmarks_edit(
    request: Request,
    id: int = Form(...),
    state_code: str = Form(...),
    state_name: str = Form(...),
    benchmark_price_per_liter: float = Form(...),
    tolerance_pct: float = Form(8.0),
    effective_date: str | None = Form(None),
):
    guard = require_auth(request)
    if guard is not None:
        return guard

    with get_db() as conn:
        update_benchmark(
            conn,
            id,
            state_code.strip().upper(),
            state_name.strip(),
            benchmark_price_per_liter,
            tolerance_pct,
            effective_date or None,
        )
    return RedirectResponse(url="/fuel-benchmarks", status_code=303)


@router.get("/fuel-benchmarks/delete")
def fuel_benchmarks_delete(request: Request, id: int):
    guard = require_auth(request)
    if guard is not None:
        return guard

    with get_db() as conn:
        delete_benchmark(conn, id)
    return RedirectResponse(url="/fuel-benchmarks", status_code=303)