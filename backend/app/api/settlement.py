"""Settlement router — settled-trip PDF listing + 1-click settlement PDF.

Migrated from `fleetflow_interactive_demo.py`'s `/settled-pdfs` and
`/generate-settlement-pdf` routes. PDF construction lives in
`services/pdf/settlement.py` so this router stays a thin HTTP wrapper.

Security:
- §2.1 unauthenticated access -> `require_auth` 303-redirects to /login.
- §2.3 stored-XSS -> DB-sourced trip/vehicle/driver values rendered via
  `security.esc()` in the HTML listing page.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response

from backend.app.core.security import esc, require_auth
from backend.app.db.connection import get_db
from backend.app.db.queries.expenses import get_expenses_for_trip
from backend.app.db.queries.settlement import get_settled_trips
from backend.app.db.queries.trips import get_trip_by_code
from backend.app.services.pdf.settlement import build_settlement_pdf
from backend.app.web.chrome import render_footer, render_header, render_sidebar

router = APIRouter()


def _fmt_dt(dt) -> str:
    return dt.strftime("%d %b %H:%M") if hasattr(dt, "strftime") else str(dt)[:16]


@router.get("/settled-pdfs", response_class=HTMLResponse)
def settled_pdf_listing(request: Request):
    guard = require_auth(request)
    if guard is not None:
        return guard

    with get_db() as conn:
        settled_trips = get_settled_trips(conn)

    pdf_rows = "".join(f"""
        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm flex flex-wrap items-center justify-between gap-4">
            <div>
                <h2 class="font-extrabold text-slate-900">{esc(trip['trip_code'])}</h2>
                <p class="text-xs text-slate-500 mt-1">{esc(trip['vehicle_no'])} · {esc(trip['driver_name'])}</p>
                <p class="text-[11px] text-slate-400 mt-2">Settled {esc(_fmt_dt(trip['settled_at'])) if trip['settled_at'] else 'date unavailable'}</p>
            </div>
            <a href="/generate-settlement-pdf?trip_code={trip['trip_code']}" target="_blank" class="bg-sky-600 hover:bg-sky-500 text-white font-bold px-4 py-2.5 rounded-xl text-xs transition shadow flex items-center gap-1.5">
                📄 View Settlement PDF
            </a>
        </div>""" for trip in settled_trips)

    return f"""<!DOCTYPE html>
    <html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>FleetFlow Settled PDFs</title><script src="https://cdn.tailwindcss.com"></script></head>
    <body class="bg-slate-100 min-h-screen p-4 md:p-6 font-sans">
        <div class="max-w-7xl mx-auto space-y-6">
            {render_header(authenticated=True)}
            <div class="flex flex-col lg:flex-row gap-4">
                {render_sidebar("settled-pdfs")}
                <main class="flex-1 space-y-4">
                    <div>
                        <h2 class="text-lg font-extrabold text-slate-900">Settled Trip PDFs</h2>
                        <p class="text-xs text-slate-500">Open settlement reconciliation PDFs for completed trips.</p>
                    </div>
                    <div class="space-y-3">{pdf_rows if pdf_rows else '<div class="bg-white border border-slate-200 rounded-2xl p-10 text-center text-sm text-slate-400">No settled trips yet.</div>'}</div>
                </main>
            </div>
            {render_footer()}
        </div>
    </body></html>"""


@router.get("/generate-settlement-pdf")
def generate_settlement_pdf(request: Request, trip_code: str):
    guard = require_auth(request)
    if guard is not None:
        return guard

    with get_db() as conn:
        trip = get_trip_by_code(conn, trip_code)
        if not trip:
            return Response("Trip not found", status_code=404)
        expenses = get_expenses_for_trip(conn, trip_code)

    pdf_bytes = build_settlement_pdf(trip, expenses)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={trip_code}_Settlement.pdf"},
    )