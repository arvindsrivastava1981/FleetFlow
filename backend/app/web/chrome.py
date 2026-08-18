"""Shared HTML chrome (header, footer, sidebar).

Role-based navigation: the sidebar shows different links depending on the
user's role (super_admin / trip_manager / driver). The header shows the
logged-in user's name and role badge.

These helpers render only static markup + trusted booleans; no user-sourced
data is interpolated here, so no escaping is needed at this layer. Page
builders that do insert driver/expense values MUST route them through
`core.security.esc()` first (stored-XSS fix, §2.3).
"""
from __future__ import annotations

from backend.app.core.security import esc


# Canonical product brand. The app was historically named "FleetFlow" (shown
# as "FF"); the product was renamed to VahanKhata everywhere (README,
# render.yaml service name, all page <title> tags, footer). This single
# constant is the source of truth for the logged-in chrome header, so the
# header can never silently drift back to the old brand again.
_BRAND_MARK = "VK"
_BRAND_NAME = "VahanKhata"


_ROLE_LABELS: dict[str, str] = {
    "super_admin": "Super Admin",
    "trip_manager": "Trip Manager",
    "driver": "Driver",
}


def render_header(authenticated: bool = False, username: str = "", role: str = "") -> str:
    if authenticated:
        role_label = _ROLE_LABELS.get(role, "")
        role_badge = (
            f'<span class="text-[10px] font-bold px-2 py-0.5 rounded-full '
            f'bg-sky-900 text-sky-200 ml-1">{esc(role_label)}</span>'
            if role_label
            else ""
        )
        auth_controls = (
            f'<span class="text-xs text-slate-300 font-semibold">'
            f'Welcome, <span class="text-sky-300">{esc(username)}</span>{role_badge}'
            f'</span>'
            f'<a href="/logout" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold px-3 py-2 rounded-xl transition">Logout</a>'
        )
        nav_links = ""
    else:
        nav_links = ""
        auth_controls = (
            '<a href="/login" class="bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold px-3 py-2 rounded-xl transition">Login</a>'
        )

    return f'''
        <header class="bg-slate-900 text-white p-5 rounded-2xl flex flex-wrap justify-between items-center shadow-lg gap-4">
            <div class="flex items-center space-x-3">
                <div class="bg-sky-500 p-2 rounded-xl text-white font-black text-xl">{_BRAND_MARK}</div>
                <div>
                    <h1 class="text-xl font-extrabold tracking-tight">{_BRAND_NAME}</h1>
                    <p class="text-xs text-sky-400 font-medium">Real-Time Expense Verification & Settlement Engine</p>
                </div>
            </div>
            <nav class="flex items-center gap-3">{nav_links}{auth_controls}</nav>
        </header>'''


def render_footer() -> str:
    return '''
        <footer class="text-center text-xs text-slate-400 py-2">
            VahanKhata · Expense verification and settlement
        </footer>'''


def _nav_link(href: str, label: str, icon: str, key: str, active: str, badge: str = "") -> str:
    classes = (
        "bg-sky-600 text-white"
        if active == key
        else "text-slate-300 hover:bg-slate-800 hover:text-white"
    )
    badge_html = (
        f'<span class="ml-auto bg-amber-500 text-white text-[10px] font-bold px-1.5 '
        f'py-0.5 rounded-full">{badge}</span>'
        if badge
        else ""
    )
    return (
        f'<a href="{href}" class="flex items-center gap-2 px-3 py-2 '
        f'rounded-lg text-[13px] font-semibold transition {classes}">'
        f'<span class="w-5 text-center">{icon}</span> <span>{label}</span>{badge_html}</a>'
    )


def _nav_section(title: str) -> str:
    return (
        f'<p class="px-3 pt-3 pb-1 text-[10px] font-bold uppercase tracking-wider '
        f'text-slate-500">{title}</p>'
    )


def render_sidebar(active: str, role: str = "super_admin") -> str:
    """Render the grouped, role-aware sidebar navigation."""
    links: list[str] = []

    # Dashboard target varies by role.
    dashboard_href = {"super_admin": "/admin", "trip_manager": "/manager",
                      "driver": "/driver"}.get(role, "/dashboard")
    dashboard_key = {"super_admin": "admin", "trip_manager": "manager",
                     "driver": "driver"}.get(role, "dashboard")

    # ── OPERATIONS ──────────────────────────────────────────────────────
    links.append(_nav_section("Operations"))
    links.append(_nav_link(dashboard_href, "My Dashboard", "📊", dashboard_key, active))
    links.append(_nav_link("/trips", "Active Trips", "🚚", "trips", active))
    links.append(_nav_link("/", "Expense Ledger", "🧾", "expense-ledger", active == "ledger"))
    links.append(
        _nav_link("/dashboard", "Fraud Alerts", "⚠️", "fraud-alerts", active == "fraud-alerts", "Live")
    )
    links.append(_nav_link("/settled-pdfs", "Trip Settlements", "📑", "settled-pdfs", active))

    # ── FLEET & ASSETS (super_admin + trip_manager only) ───────────────
    if role in ("super_admin", "trip_manager"):
        links.append(_nav_section("Fleet & Assets"))
        if role == "super_admin":
            links.append(_nav_link("/fleets", "Fleets", "🏢", "fleets", active))
        links.append(_nav_link("/vehicles", "Vehicles", "🚛", "vehicles", active))
        links.append(_nav_link("/drivers", "Drivers", "👤", "drivers", active))
        links.append(_nav_link("/fuel-benchmarks", "Fuel Benchmarks", "⛽", "fuel-benchmarks", active))

    if role == "super_admin":
        # ── SYSTEM & REPORTS ────────────────────────────────────────────────
        links.append(_nav_section("System & Reports"))
        links.append(_nav_link("/dashboard", "Analytics & Reports", "📈", "analytics", active == "analytics"))
        links.append(_nav_link("/users", "Organization Settings", "⚙️", "users", active))

        # ── ACCOUNT & SECURITY ──────────────────────────────────────────────
        links.append(_nav_section("Account & Security"))
        links.append(_nav_link("/users/change-password", "Change Password", "🔒", "users/change-password", active))
    else:
        # ── ACCOUNT ─────────────────────────────────────────────────────────
        links.append(_nav_section("Account"))
        links.append(_nav_link("/users/change-password", "Change Password", "🔒", "users/change-password", active))

    nav = "".join(links)
    return f'''
        <aside class="bg-slate-900 rounded-2xl p-3 w-full lg:w-56 flex-shrink-0 space-y-1 h-fit">
            {nav}
        </aside>'''
