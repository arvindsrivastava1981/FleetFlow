import { useState } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import NotificationBell from "./NotificationBell.jsx";
import ErrorBoundary from "./ErrorBoundary.jsx";
import SessionWarningBanner from "./SessionWarningBanner.jsx";

const SECTIONS = [
  {
    title: "Onboarding",
    roles: ["super_admin"],
    links: [
      { to: "/onboard", label: "Onboard Firm", icon: "🚧", roles: ["super_admin"] },
    ],
  },
  {
    title: "Operations",
    links: [
      { to: "/dashboard", label: "My Dashboard", icon: "📊" },
      { to: "/trips", label: "Active Trips", icon: "🚚", roles: ["trip_manager", "super_admin"] },
      {
        to: "/whatsapp",
        icon: "💬",
        label: (role) => (role === "driver" ? "WhatsApp View" : "Expense Approvals"),
      },
      { to: "/driver-salary", label: "Driver Salary", icon: "💰", roles: ["driver"] },
      { to: "/settlements", label: "Settled Trips", icon: "📒" },
    ],
  },
  {
    title: "Fleet & Assets",
    links: [
      { to: "/fleets", label: "Fleets", icon: "🏢", roles: ["super_admin"] },
      { to: "/vehicles", label: "Vehicles", icon: "🚛", roles: ["trip_manager", "super_admin"] },
      { to: "/drivers", label: "Drivers", icon: "👨", roles: ["trip_manager", "super_admin"] },
      { to: "/benchmarks", label: "Rules & Rates", icon: "⚖️", roles: ["trip_manager", "super_admin"] },
    ],
  },
  {
    title: "System & Reports",
    roles: ["super_admin"],
    links: [
      { to: "/users", label: "Users", icon: "👨", roles: ["super_admin"] },
      { to: "/analytics", label: "Analytics", icon: "📈", roles: ["super_admin"] },
    ],
  },
];

const ROLE_LABELS = {
  super_admin: "Super Admin",
  trip_manager: "Trip Manager",
  driver: "Driver",
};

// Audit P-6: persisted HI/EN toggle for the navigation chrome. Page content
// stays bilingual at the source (label_en/label_hi payloads); this covers the
// sidebar labels users see on every screen.
const SECTION_I18N_HI = {
  Onboarding: "ऑनबोर्डिंग",
  Operations: "संचालन",
  "Fleet & Assets": "बेड़ा व संसाधन",
  "System & Reports": "सिस्टम व रिपोर्ट",
  Account: "खाता",
};
const LINK_I18N_HI = {
  "/onboard": "फर्म जोड़ें",
  "/dashboard": "मेरा डैशबोर्ड",
  "/trips": "सक्रिय ट्रिप",
  "/driver-salary": "ड्राइवर वेतन",
  "/settlements": "निपटान ट्रिप",
  "/fleets": "बेड़े",
  "/vehicles": "वाहन",
  "/drivers": "ड्राइवर",
  "/benchmarks": "नियम व दरें",
  "/users": "उपयोगकर्ता",
  "/subscription": "सदस्यता",
  "/change-password": "पासवर्ड बदलें",
};
function navLang() {
  try {
    return localStorage.getItem("vk_lang") === "hi" ? "hi" : "en";
  } catch {
    return "en";
  }
}

function navClass({ isActive }) {
  return `flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition ${
    isActive
      ? "bg-brand-50 font-semibold text-brand-700"
      : "font-medium text-ink-600 hover:bg-ink-100 hover:text-ink-900"
  }`;
}
      function Sidebar({ role }) {
  const { logout } = useAuth();
  const [lang, setLang] = useState(navLang()); // audit P-6
  const hi = lang === "hi";
  const tSection = (title) => (hi ? SECTION_I18N_HI[title] || title : title);
  const tLink = (label) => (hi && LINK_I18N_HI[label]) || label;
  const toggleLang = () => {
    const next = hi ? "en" : "hi";
    try {
      localStorage.setItem("vk_lang", next);
    } catch { /* private mode: session-only fallback */ }
    setLang(next);
  };
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
              {tSection(section.title)}
            </p>
            <div className="space-y-0.5">
              {links.map((link) => {
                const rawLabel =
                  typeof link.label === "function" ? link.label(role) : link.label;
                const label = hi ? tLink(rawLabel) : rawLabel;
                return (
                  <NavLink
                    key={link.to}
                    to={link.to}
                    end={link.to === "/trips"}
                    className={navClass}
                  >
                    <span className="w-5 text-center text-base leading-none">
                      {link.icon}
                    </span>
                    <span>{label}</span>
                  </NavLink>
                );
              })}
            </div>
          </div>
        );
      })}

      <div>
        <p className="px-3 pb-1.5 text-[11px] font-bold uppercase tracking-wider text-ink-400">
          {tSection("Account")}
        </p>
        <div className="space-y-0.5">
          <button
            type="button"
            onClick={toggleLang}
            className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-medium text-ink-600 transition hover:bg-brand-50 hover:text-brand-700"
          >
            <span className="w-5 text-center text-base leading-none">🌐</span>
            <span>{hi ? "English" : "हिंदी में"}</span>
          </button>
          {role !== "driver" && (
            <NavLink to="/subscription" className={navClass}>
              <span className="w-5 text-center text-base leading-none">💳</span>
              <span>{tLink("/subscription")}</span>
            </NavLink>
          )}
          <NavLink to="/change-password" className={navClass}>
            <span className="w-5 text-center text-base leading-none">🔒</span>
            <span>{tLink("/change-password")}</span>
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
        <div className="border-b border-ink-200 bg-white px-4 py-3 shadow-sm lg:hidden">
          <Sidebar role={role} />
        </div>
      )}

      <div className="mx-auto flex max-w-screen-2xl items-start gap-6 px-4 py-6 md:px-6">
        <aside className="sticky top-[73px] hidden w-60 flex-shrink-0 self-start lg:block">
          <div className="card p-2">
            <Sidebar role={role} />
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
