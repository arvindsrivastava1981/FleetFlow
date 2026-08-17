"""Shared HTML chrome (header, footer, sidebar).

Moved from `utils.py` (`render_header`, `render_footer`, `render_sidebar`).
These helpers render only static markup + trusted booleans; no user-sourced
data is interpolated here, so no escaping is needed at this layer. Page
builders that do insert driver/expense values MUST route them through
`core.security.esc()` first (stored-XSS fix, §2.3).
"""
from __future__ import annotations


def render_header(authenticated: bool = False) -> str:
    nav_links = (
        '''<a href="/dashboard" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold px-3 py-2 rounded-xl transition">📊 Dashboard</a>
            <a href="/trips" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold px-3 py-2 rounded-xl transition">🧾 Trips</a>'''
        if authenticated
        else ""
    )
    auth_controls = (
        '''<span class="text-xs text-slate-300 font-semibold">Welcome </span>
            <a href="/logout" class="bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold px-3 py-2 rounded-xl transition">🚪 Logout</a>'''
        if authenticated
        else '''<a href="/login" class="bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold px-3 py-2 rounded-xl transition">Login</a>'''
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


def render_sidebar(active: str) -> str:
    def _nav_link(href: str, label: str, icon: str, key: str) -> str:
        classes = (
            "bg-sky-600 text-white"
            if active == key
            else "text-slate-300 hover:bg-slate-800 hover:text-white"
        )
        return (
            f'<a href="{href}" class="flex items-center gap-2 px-4 py-2.5 '
            f'rounded-xl text-sm font-semibold transition {classes}">{icon} {label}</a>'
        )

    return f'''
        <aside class="bg-slate-900 rounded-2xl p-3 w-full lg:w-52 flex-shrink-0 space-y-1 h-fit">
            {_nav_link("/dashboard", "Dashboard", "📊", "dashboard")}
            {_nav_link("/trips", "Trips", "🧾", "trips")}
            {_nav_link("/settled-pdfs", "Settled PDFs", "📄", "settled-pdfs")}
            {_nav_link("/fuel-benchmarks", "Fuel Benchmarks", "⛽", "fuel-benchmarks")}
            {_nav_link("/rule-engine", "Rule Engine", "⚙️", "rule-engine")}
            {_nav_link("/logout", "Logout", "🚪", "logout")}
        </aside>'''