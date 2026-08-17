"""Rule-engine explainer page — read-only view.

Migrated from `fleetflow_interactive_demo.py`'s `/rule-engine` route so the
sidebar link resolves (was a 404 in the modular app). Renders the anomaly
rules per expense type using only trusted `settings` constants — no DB-sourced
values are interpolated, so no per-value escaping is needed (§2.3).
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from backend.app.core.config import settings
from backend.app.core.security import require_auth
from backend.app.web.chrome import render_footer, render_header, render_sidebar

router = APIRouter()


def _rule_card(exp_type: str, badge_color: str, rules: list[str]) -> str:
    items = "".join(
        f'<li class="text-xs text-slate-600 leading-relaxed">{r}</li>' for r in rules
    )
    return f"""<div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
        <span class="text-[10px] font-bold px-2 py-0.5 rounded-full {badge_color}">{exp_type}</span>
        <ul class="list-disc list-inside mt-3 space-y-1.5">{items}</ul>
    </div>"""


@router.get("/rule-engine", response_class=HTMLResponse)
def rule_engine_page(request: Request):
    guard = require_auth(request)
    if guard is not None:
        return guard

    cards = "".join([
        _rule_card("FUEL", "bg-amber-100 text-amber-800", [
            "<b>Math integrity:</b> flags if Amount differs from Liters × Rate by more than ₹10.",
            f"<b>Price benchmark:</b> flags if rate is outside ₹82–₹98/L band (base ₹{settings.benchmark_price}/L).",
            f"<b>Tank capacity:</b> flags if claimed liters exceed {settings.tank_capacity_liters:.0f}L max tank size.",
            "<b>Odometer rollback:</b> flags if new odometer reading is less than the previous fuel reading.",
            f"<b>Mileage check:</b> flags if calculated km/L falls below 70% of expected {settings.expected_kml:.1f} km/L (i.e. under 2.8 km/L).",
        ]),
        _rule_card("TOLL", "bg-rose-100 text-rose-800", [
            "Always flagged — cash toll claims are disallowed on FASTag-mandated corridors.",
        ]),
        _rule_card("REPAIR", "bg-orange-100 text-orange-800", [
            "Flags any repair claim above ₹3,000 as requiring owner pre-approval.",
        ]),
        _rule_card("CHALLAN", "bg-rose-100 text-rose-800", [
            "Always flagged — traffic challans must be verified against the e-challan portal.",
        ]),
        _rule_card("DEF", "bg-indigo-100 text-indigo-800", [
            f"<b>Price benchmark:</b> flags if DEF/AdBlue rate exceeds ₹{settings.def_rate_max:.0f}/L ceiling.",
            f"<b>Consumption ratio:</b> flags if cumulative DEF volume falls outside {settings.def_min_ratio_pct:.0f}–{settings.def_max_ratio_pct:.0f}% of cumulative diesel volume.",
        ]),
        _rule_card("RTO-FINE", "bg-rose-100 text-rose-800", [
            "Always flagged — RTO fines always require owner review.",
        ]),
    ])

    return f"""<!DOCTYPE html>
    <html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>FleetFlow Rule Engine</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-7xl mx-auto space-y-6">
            {render_header(authenticated=True)}
            <div class="flex flex-col lg:flex-row gap-4">
                {render_sidebar("rule-engine")}
                <main class="flex-1 space-y-4">
                    <div>
                        <h2 class="text-lg font-extrabold text-slate-900">Rule Engine</h2>
                        <p class="text-xs text-slate-500">Automated checks applied to every expense claim via WhatsApp simulation, grouped by expense type.</p>
                    </div>
                    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                        {cards}
                    </div>
                </main>
            </div>
            {render_footer()}
        </div>
    </body></html>"""
