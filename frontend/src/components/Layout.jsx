import { NavLink, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

const SECTIONS = [
  {
    title: "Operations",
    links: [
      { to: "/dashboard", label: "My Dashboard", icon: "📊" },
      { to: "/trips", label: "Active Trips", icon: "🚚", roles: ["trip_manager", "super_admin"] },
      { to: "/expenses", label: "Expense Ledger", icon: "🧾" },
      { to: "/settlements", label: "Settled Trips", icon: "📑" },
    ],
  },
  {
    title: "Fleet & Assets",
    links: [
      { to: "/vehicles", label: "Vehicles", icon: "🚛", roles: ["trip_manager", "super_admin"] },
      { to: "/drivers", label: "Drivers", icon: "👤", roles: ["trip_manager", "super_admin"] },
    ],
  },
  {
    title: "System & Reports",
    roles: ["super_admin"],
    links: [
      { to: "/users", label: "Users", icon: "👤", roles: ["super_admin"] },
      { to: "/fleets", label: "Fleets", icon: "🏢", roles: ["super_admin"] },
      { to: "/benchmarks", label: "Fuel Benchmarks", icon: "⛽", roles: ["super_admin"] },
    ],
  },
];

function Sidebar({ role }) {
  const { logout } = useAuth();
  return (
    <aside className="bg-slate-900 rounded-2xl p-3 w-full lg:w-56 flex-shrink-0 space-y-1 h-fit">
      {SECTIONS.filter(
        (s) => !s.roles || s.roles.includes(role)
      ).map((section) => (
        <div key={section.title}>
          <p className="px-3 pt-3 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">
            {section.title}
          </p>
          {section.links
            .filter((l) => !l.roles || l.roles.includes(role))
            .map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-lg text-[13px] font-semibold transition ${
                    isActive
                      ? "bg-sky-600 text-white"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`
                }
              >
                <span className="w-5 text-center">{link.icon}</span>
                <span>{link.label}</span>
              </NavLink>
            ))}
        </div>
      ))}
      <div>
        <p className="px-3 pt-3 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          Account
        </p>
        <NavLink
          to="/change-password"
          className={({ isActive }) =>
            `flex items-center gap-2 px-3 py-2 rounded-lg text-[13px] font-semibold transition ${
              isActive
                ? "bg-sky-600 text-white"
                : "text-slate-300 hover:bg-slate-800 hover:text-white"
            }`
          }
        >
          <span className="w-5 text-center">🔒</span>
          <span>Change Password</span>
        </NavLink>
        <button
          onClick={logout}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-[13px] font-semibold text-slate-300 hover:bg-slate-800 hover:text-white transition"
        >
          <span className="w-5 text-center">🚪</span>
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}

export default function Layout({ children }) {
  const { user } = useAuth();
  const role = user?.role || "super_admin";
  return (
    <div className="min-h-screen bg-slate-100 p-4 md:p-6 font-sans">
      <div className="max-w-7xl mx-auto space-y-6">
        <header className="bg-slate-900 text-white p-5 rounded-2xl flex flex-wrap justify-between items-center shadow-lg gap-4">
          <div className="flex items-center space-x-3">
            <div className="bg-sky-500 p-2 rounded-xl text-white font-black text-xl">VK</div>
            <div>
              <h1 className="text-xl font-extrabold tracking-tight">VahanKhata</h1>
              <p className="text-xs text-sky-400 font-medium">
                Real-Time Expense Verification & Settlement Engine
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-300 font-semibold">
              Welcome, <span className="text-sky-300">{user?.username}</span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-sky-900 text-sky-200 ml-1">
                {role}
              </span>
            </span>
          </div>
        </header>
        <div className="flex flex-col lg:flex-row gap-4">
          <Sidebar role={role} />
          <main className="flex-1 min-w-0">{children}</main>
        </div>
      </div>
    </div>
  );
}