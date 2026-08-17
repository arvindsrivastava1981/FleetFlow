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
        nav_links = (
            '<a href="/dashboard" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold px-3 py-2 rounded-xl transition">Dashboard</a>'
        )
    else:
        nav_links = ""
        auth_controls = (
            '<a href="/login" class="bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold px-3 py-2 rounded-xl transition">Login</a>'
        )

    return f'''
        <header class="bg-slate-900 text-white p-5 rounded-2xl flex flex-wrap justify-between items-center shadow-lg gap-4">
            <div class="flex items-center space-x-3">
                <div class="bg-sky-500 p-2 rounded-xl text-white font-black text-xl">FF</div>
                <div>
                    <h1 class="text-xl font-extrabold tracking-tight">FleetFlow</h1>
                    <p class="text-xs text-sky-400 font-medium">Real-Time Expense Verification & Settlement Engine</p>
                </div>
            </div>
            <nav class="flex items-center gap-3">{nav_links}{auth_controls}</nav>
        </header>'''


def render_footer() -> str:
    return '''
        <footer class="text-center text-xs text-slate-400 py-2">
            FleetFlow · Expense verification and settlement
        </footer>'''


def _nav_link(href: str, label: str, icon: str, key: str, active: str) -> str:
    classes = (
        "bg-sky-600 text-white"
        if active == key
        else "text-slate-300 hover:bg-slate-800 hover:text-white"
    )
    return (
        f'<a href="{href}" class="flex items-center gap-2 px-4 py-2.5 '
        f'rounded-xl text-sm font-semibold transition {classes}">{icon} {label}</a>'
    )


def render_sidebar(active: str, role: str = "super_admin") -> str:
    """Render the sidebar with role-appropriate nav links."""
    links: list[str] = []

    # Dashboard is available to all roles
    links.append(_nav_link("/dashboard", "Dashboard", "📊", "dashboard", active))

    if role == "super_admin":
        links.append(_nav_link("/users", "Manage Users", "👥", "users", active))
        links.append(_nav_link("/trips", "All Trips", "🧾", "trips", active))
        links.append(_nav_link("/settled-pdfs", "Settled PDFs", "📄", "settled-pdfs", active))
        links.append(_nav_link("/fuel-benchmarks", "Fuel Benchmarks", "⛽", "fuel-benchmarks", active))
        links.append(_nav_link("/rule-engine", "Rule Engine", "⚙️", "rule-engine", active))
    elif role == "trip_manager":
        links.append(_nav_link("/drivers", "Manage Drivers", "👥", "drivers", active))
        links.append(_nav_link("/trips", "My Trips", "🧾", "trips", active))
        links.append(_nav_link("/settled-pdfs", "My Settled PDFs", "📄", "settled-pdfs", active))
        links.append(_nav_link("/rule-engine", "Rule Engine", "⚙️", "rule-engine", active))
    # driver
    links.append(_nav_link("/driver/trips", "Active Trips", "🚗", "driver-trips", active))
    links.append(_nav_link("/driver/settled", "Settled Trips", "📄", "driver-settled", active))

    links.append(_nav_link("/users/change-password", "Change Password", "🚪", "users/change-password", active))

    links.append(_nav_link("/logout", "Logout", "🚪", "logout", active))

    nav = "".join(links)
    return f'''
        <aside class="bg-slate-900 rounded-2xl p-3 w-full lg:w-52 flex-shrink-0 space-y-1 h-fit">
            {nav}
        </aside>'''
