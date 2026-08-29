import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import NotificationBell from "./NotificationBell.jsx";
import ErrorBoundary from "./ErrorBoundary.jsx";
import SessionWarningBanner from "./SessionWarningBanner.jsx";

const SECTIONS = [
  {
    title: "Onboarding",
    titleHi: "ऑनबोर्डिंग",
    roles: ["super_admin"],
    links: [
      { to: "/onboard", label: "Onboard Firm", labelHi: "फर्म जोड़ें", icon: "🚧", roles: ["super_admin"] },
    ],
  },
  {
    title: "Operations",
    titleHi: "संचालन",
    links: [
      { to: "/dashboard", label: "My Dashboard", labelHi: "मेरा डैशबोर्ड", icon: "📊" },
      { to: "/trips", label: "Active Trips", labelHi: "सक्रिय ट्रिप", icon: "🚚", roles: ["trip_manager", "super_admin"] },
      {
        to: "/whatsapp",
        icon: "💬",
        label: (role) => (role === "driver" ? "WhatsApp View" : "Expense Approvals"),
        labelHi: (role) => (role === "driver" ? "व्हाट्सऐप व्यू" : "खर्च स्वीकृति"),
      },
      { to: "/driver-salary", label: "Driver Salary", labelHi: "ड्राइवर वेतन", icon: "💰", roles: ["driver"] },
      { to: "/settlements", label: "Settled Trips", labelHi: "निपटान ट्रिप", icon: "📒" },
    ],
  },
  {
    title: "Fleet & Assets",
    titleHi: "बेड़ा व संसाधन",
    links: [
      { to: "/fleets", label: (r) => (r === "trip_manager" ? "My Fleet" : "Fleets"), labelHi: "बेड़े", icon: "🏢", roles: ["trip_manager", "super_admin"] },
      { to: "/vehicles", label: "Vehicles", labelHi: "वाहन", icon: "🚛", roles: ["trip_manager", "super_admin"] },
      { to: "/drivers", label: "Drivers", labelHi: "ड्राइवर", icon: "👨", roles: ["trip_manager", "super_admin"] },
    ],
  },
  {
    title: "Settings",
    titleHi: "सेटिंग्स",
    roles: ["trip_manager", "super_admin"],
    links: [
      { to: "/benchmarks", label: "Rules & Rates", labelHi: "नियम व दरें", icon: "⚖️", roles: ["trip_manager", "super_admin"] },
    ],
  },
  {
    title: "System & Reports",
    titleHi: "सिस्टम व रिपोर्ट",
    roles: ["super_admin"],
    links: [
      { to: "/users", label: "Users", labelHi: "उपयोगकर्ता", icon: "👨", roles: ["super_admin"] },
      { to: "/analytics", label: "Analytics", labelHi: "एनालिटिक्स", icon: "📈", roles: ["trip_manager", "super_admin"] },
      { to: "/error-logs", label: "Error Logs", labelHi: "एरर लॉग", icon: "🚨", roles: ["super_admin"] },
    ],
  },
];

const ROLE_LABELS = {
  super_admin: "Super Admin",
  trip_manager: "Trip Manager",
  driver: "Driver",
};

// Audit P-6: persisted HI/EN toggle covering the full sidebar chrome (section
// headers, every link, and the Account items). The language state lives in
// <Layout> so the desktop and mobile sidebar instances stay in sync; the
// choice persists in localStorage ("vk_lang").
function navLang() {
  try {
    return localStorage.getItem("vk_lang") === "hi" ? "hi" : "en";
  } catch {
    return "en";
  }
}

function navClass({ isActive }) {
  return `group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all duration-200 ${
    isActive
      ? "bg-brand-50 font-semibold text-brand-700 shadow-sm"
      : "font-medium text-ink-600 hover:bg-ink-100 hover:text-ink-900"
  }`;
}
function Sidebar({ role, lang = "en", onToggleLang }) {
  const { logout, user } = useAuth();
  const hi = lang === "hi";
  // Fleet-less trip managers are gated to /onboarding by ProtectedRoute — hide
  // nav links that would just bounce so the sidebar never shows dead entries.
  const fleetless = role === "trip_manager" && !user?.fleet_id;
  const sections = SECTIONS.filter((s) => !s.roles || s.roles.includes(role));
  const resolve = (value) => (typeof value === "function" ? value(role) : value);
  const labelFor = (link) => {
    const en = resolve(link.label);
    return hi ? resolve(link.labelHi) || en : en;
  };

  return (
    <nav className="flex flex-col gap-5">
      {/* Language switch pinned to the top of the sidebar (audit P-6). */}
      <div className="flex items-center justify-between rounded-lg border border-ink-200 bg-white px-3 py-2">
        <span className="text-xs font-bold uppercase tracking-wider text-ink-400">
          {hi ? "भाषा" : "Language"}
        </span>
        <div className="flex items-center gap-2">
          <span className={`text-[11px] font-bold ${!hi ? "text-brand-700" : "text-ink-400"}`}>
            EN
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={hi}
            aria-label={hi ? "Switch to English" : "हिंदी में बदलें"}
            onClick={onToggleLang}
            className={`relative inline-flex h-5 w-9 flex-shrink-0 cursor-pointer rounded-full transition-colors ${
              hi ? "bg-brand-600" : "bg-ink-300"
            }`}
          >
            <span
              className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform ${
                hi ? "translate-x-4" : "translate-x-0.5"
              }`}
            />
          </button>
          <span className={`text-[11px] font-bold ${hi ? "text-brand-700" : "text-ink-400"}`}>
            हिं
          </span>
        </div>
      </div>

      {fleetless && (
        <NavLink to="/onboarding" className={navClass}>
          <span className="w-5 text-center text-base leading-none">🚧</span>
          <span>{hi ? "फर्म सेटअप पूरा करें" : "Finish Firm Setup"}</span>
        </NavLink>
      )}

      {sections.map((section) => {
        const links = section.links.filter(
          (l) =>
            (!l.roles || l.roles.includes(role)) &&
            !(fleetless && l.to !== "/dashboard")
        );
        if (!links.length) return null;
        return (
          <div key={section.title}>
            <p className="px-3 pb-1.5 text-[11px] font-bold uppercase tracking-wider text-ink-400">
              {hi ? section.titleHi || section.title : section.title}
            </p>
            <div className="space-y-0.5">
              {links.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  end={link.to === "/trips"}
                  className={navClass}
                >
                  {({ isActive }) => (
                    <>
                      <span
                        aria-hidden="true"
                        className={`absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-brand-600 transition-all duration-200 ${
                          isActive ? "opacity-100" : "opacity-0"
                        }`}
                      />
                      <span className="w-5 text-center text-base leading-none">
                        {link.icon}
                      </span>
                      <span>{labelFor(link)}</span>
                    </>
                  )}
                </NavLink>
              ))}
            </div>
          </div>
        );
      })}

      <div>
        <p className="px-3 pb-1.5 text-[11px] font-bold uppercase tracking-wider text-ink-400">
          {hi ? "खाता" : "Account"}
        </p>
        <div className="space-y-0.5">
          {role === "trip_manager" && !fleetless && (
            <NavLink to="/subscription" className={navClass}>
              <span className="w-5 text-center text-base leading-none">💳</span>
              <span>{hi ? "सदस्यता" : "Subscription"}</span>
            </NavLink>
          )}
          <NavLink to="/change-password" className={navClass}>
            <span className="w-5 text-center text-base leading-none">🔒</span>
            <span>{hi ? "पासवर्ड बदलें" : "Change Password"}</span>
          </NavLink>
          <button
            onClick={logout}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-medium text-ink-600 transition hover:bg-rose-50 hover:text-rose-700"
          >
            <span className="w-5 text-center text-base leading-none">🚪</span>
            <span>{hi ? "लॉग आउट" : "Logout"}</span>
          </button>
        </div>
      </div>
    </nav>
  );
}

export default function Layout({ children }) {
  const { user } = useAuth();
  const role = user?.role || "super_admin";
  const [mobileNavOpen, setMobileNavOpen] = useState(false); // audit E-7
  const [lang, setLang] = useState(navLang()); // audit P-6: shared HI/EN state

  const toggleLang = () => {
    setLang((prev) => {
      const next = prev === "hi" ? "en" : "hi";
      try {
        localStorage.setItem("vk_lang", next);
      } catch { /* private mode: session-only fallback */ }
      return next;
    });
  };

  return (
    <div className="min-h-screen bg-ink-50 font-sans">
      <header className="sticky top-0 z-30 border-b border-ink-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between gap-4 px-4 py-3 md:px-6">
          <div className="flex items-center gap-2">
            {/* Hamburger (audit E-7): mobile drawer toggle, hidden on lg+. */}
            <button
              type="button"
              onClick={() => setMobileNavOpen((o) => !o)}
              aria-label={mobileNavOpen ? "Close menu" : "Open menu"}
              aria-expanded={mobileNavOpen}
              className="flex h-9 w-9 items-center justify-center rounded-lg border border-ink-200 bg-white text-base shadow-sm transition hover:bg-ink-50 lg:hidden"
            >
              {mobileNavOpen ? "✕" : "☰"}
            </button>
            <Brand />
          </div>
          <div className="flex items-center gap-3">
            <NotificationBell />
            <UserChip user={user} role={role} />
          </div>
        </div>
      </header>

      {/* Audit E-10: warn before the hard logout; offer one-click renewal. */}
      <SessionWarningBanner />

      {/* Mobile nav drawer (audit E-7): replaces the old always-stacked card. */}
      {mobileNavOpen && (
        <>
          <div
            className="fixed inset-0 z-20 bg-ink-900/40 backdrop-blur-sm lg:hidden"
            aria-hidden="true"
            onClick={() => setMobileNavOpen(false)}
          />
          <div className="relative z-20 border-b border-ink-200 bg-white px-4 py-3 shadow-sm lg:hidden">
            <Sidebar role={role} lang={lang} onToggleLang={toggleLang} />
          </div>
        </>
      )}

      <div className="mx-auto flex max-w-screen-2xl items-start gap-6 px-4 py-6 md:px-6">
        <aside className="sticky top-[73px] hidden w-60 flex-shrink-0 self-start lg:block">
          <div className="card p-2">
            <Sidebar role={role} lang={lang} onToggleLang={toggleLang} />
          </div>
        </aside>

        <main className="min-w-0 flex-1 pb-10">
          <ErrorBoundary>{children}</ErrorBoundary>
        </main>
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
  const initials = ((user?.full_name || user?.email || "U").slice(0, 2)).toUpperCase();
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
          {user?.full_name || user?.email}
        </span>
      </div>
    </div>
  );
}
