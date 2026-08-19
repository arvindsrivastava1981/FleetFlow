import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

const SECTIONS = [
  {
    title: "Operations",
    links: [
      { to: "/dashboard", label: "My Dashboard", icon: "📊" },
      { to: "/trips", label: "Active Trips", icon: "🚚", roles: ["trip_manager", "super_admin"] },
      { to: "/expenses", label: "Expense Ledger", icon: "🧾", roles: ["trip_manager", "super_admin"] },
      { to: "/whatsapp-driver", label: "Driver (WhatsApp)", icon: "💬", roles: ["driver"] },
      { to: "/driver-salary", label: "Driver Salary", icon: "💰", roles: ["driver"] },
      { to: "/whatsapp-manager", label: "Fleet Manager (WhatsApp)", icon: "🔔", roles: ["trip_manager", "super_admin"] },
      { to: "/settlements", label: "Settled Trips", icon: "📑" },
      { to: "/billing", label: "Billing", icon: "💳", roles: ["trip_manager", "super_admin"] },
      { to: "/rule-engine", label: "Rule Engine", icon: "⚙️", roles: ["trip_manager", "super_admin"] },
    ],
  },
  {
    title: "Fleet & Assets",
    links: [
      { to: "/fleets", label: "Fleets", icon: "🏢", roles: ["trip_manager", "super_admin"] },
      { to: "/vehicles", label: "Vehicles", icon: "🚛", roles: ["trip_manager", "super_admin"] },
      { to: "/drivers", label: "Drivers", icon: "👤", roles: ["trip_manager", "super_admin"] },
    ],
  },
  {
    title: "System & Reports",
    roles: ["super_admin"],
    links: [
      { to: "/onboard", label: "Onboard Firm", icon: "🏗️", roles: ["super_admin"] },
      { to: "/users", label: "Users", icon: "👤", roles: ["super_admin"] },
      { to: "/benchmarks", label: "Fuel Benchmarks", icon: "⛽", roles: ["super_admin"] },
    ],
  },
];

const ROLE_LABELS = {
  super_admin: "Super Admin",
  trip_manager: "Trip Manager",
  driver: "Driver",
};

function navClass({ isActive }) {
  return `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
    isActive
      ? "bg-brand-50 font-semibold text-brand-700"
      : "font-medium text-ink-600 hover:bg-ink-100 hover:text-ink-900"
  }`;
}
      function Sidebar({ role }) {
  const { logout } = useAuth();
  const sections = SECTIONS.filter((s) => !s.roles || s.roles.includes(role));

  return (
    <nav className="flex flex-col gap-6">
      {sections.map((section) => {
        const links = section.links.filter(
          (l) => !l.roles || l.roles.includes(role)
        );
        if (!links.length) return null;
        return (
          <div key={section.title}>
            <p className="px-3 pb-1.5 text-[11px] font-bold uppercase tracking-wider text-ink-400">
              {section.title}
            </p>
            <div className="space-y-0.5">
              {links.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.to === "/trips"}
                  className={navClass}
                >
                  <span className="w-5 text-center text-base leading-none">
                    {link.icon}
                  </span>
                  <span>{link.label}</span>
                </NavLink>
              ))}
            </div>
          </div>
        );
      })}

      <div>
        <p className="px-3 pb-1.5 text-[11px] font-bold uppercase tracking-wider text-ink-400">
          Account
        </p>
        <div className="space-y-0.5">
          <NavLink to="/change-password" className={navClass}>
            <span className="w-5 text-center text-base leading-none">🔒</span>
            <span>Change Password</span>
          </NavLink>
          <button
            onClick={logout}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-medium text-ink-600 transition hover:bg-rose-50 hover:text-rose-700"
          >
            <span className="w-5 text-center text-base leading-none">🚪</span>
            <span>Logout</span>
          </button>
        </div>
      </div>
    </nav>
  );
}

export default function Layout({ children }) {
  const { user } = useAuth();
  const role = user?.role || "super_admin";

  return (
    <div className="min-h-screen bg-ink-50 font-sans">
      <header className="sticky top-0 z-30 border-b border-ink-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between gap-4 px-4 py-3 md:px-6">
          <Brand />
          <UserChip user={user} role={role} />
        </div>
      </header>

      <div className="mx-auto flex max-w-screen-2xl items-start gap-6 px-4 py-6 md:px-6">
        <aside className="sticky top-[73px] hidden w-60 flex-shrink-0 self-start lg:block">
          <div className="card p-2">
            <Sidebar role={role} />
          </div>
        </aside>

        <div className="mb-2 w-full lg:hidden">
          <div className="card p-3">
            <Sidebar role={role} />
          </div>
        </div>

        <main className="min-w-0 flex-1 pb-10">{children}</main>
      </div>
    </div>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-brand-600 to-brand-500 text-sm font-black text-white shadow-sm">
        VK
      </div>
      <div className="leading-tight">
        <h1 className="text-base font-extrabold tracking-tight text-ink-900">
          VahanKhata
        </h1>
        <p className="hidden text-[11px] font-medium text-ink-400 sm:block">
          Fleet Expense Verification &amp; Settlement
        </p>
      </div>
    </div>
  );
}

function UserChip({ user, role }) {
  const initials = (user?.username || "U").slice(0, 2).toUpperCase();
  return (
    <div className="flex items-center gap-3">
      <span className="badge badge-brand hidden sm:inline-flex">
        {ROLE_LABELS[role] || role}
      </span>
      <div className="flex items-center gap-2 rounded-full border border-ink-200 bg-white py-1 pl-1 pr-3 shadow-sm">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">
          {initials}
        </span>
        <span className="text-sm font-semibold text-ink-700">
          {user?.username}
        </span>
      </div>
    </div>
  );
}
