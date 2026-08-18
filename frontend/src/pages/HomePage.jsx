import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";

const VALUE_PROPS = [
  {
    icon: "🧾",
    title: "Zero-Fraud Expense Ledger",
    desc: "Every fuel, toll, repair and challan is captured with receipts, odometer and photo evidence — automatically flagged against benchmarks.",
  },
  {
    icon: "⛽",
    title: "Smart Fuel Benchmarking",
    desc: "Detect overpricing and high consumption instantly against live fuel benchmarks and expected KML per vehicle.",
  },
  {
    icon: "💬",
    title: "WhatsApp Receipt Upload",
    desc: "Drivers snap and send receipts via WhatsApp-style chat. No training, no complicated apps, no manual ledgers.",
  },
  {
    icon: "📊",
    title: "Live Dashboard & Trip Control",
    desc: "Monitor active trips, pending expenses and escalation flags in real time from one single dashboard.",
  },
  {
    icon: "📑",
    title: "One-Click Settlements",
    desc: "Auto-generate clear, itemised settlement PDFs per trip. Dispute-free payouts for drivers and managers.",
  },
  {
    icon: "🚛",
    title: "Fleet & Asset Oversight",
    desc: "Vehicles, drivers, user roles and per-fleet benchmarks — full visibility across your entire fleet.",
  },
];

const PLANS = [
  {
    name: "Starter",
    emoji: "🌱",
    price: "₹499",
    period: "/month per fleet",
    tagline: "For small fleets starting to digitise expenses.",
    features: [
      "Up to 5 vehicles",
      "Up to 5 drivers",
      "Expense ledger + receipt capture",
      "Fuel benchmark checking",
      "Basic dashboard",
      "Email support",
    ],
    cta: "Login to get started",
    featured: false,
  },
  {
    name: "Growth",
    emoji: "🚀",
    price: "₹1,499",
    period: "/month per fleet",
    tagline: "Our most popular plan for growing fleets.",
    features: [
      "Up to 25 vehicles",
      "Up to 25 drivers",
      "WhatsApp receipt upload",
      "Live dashboards & trip control",
      "One-click settlement PDFs",
      "Role-based users & fleets",
      "Priority support",
    ],
    cta: "Choose Growth",
    featured: true,
  },
  {
    name: "Enterprise",
    emoji: "🏢",
    price: "Custom",
    period: "annual contract",
    tagline: "For large fleets and custom requirements.",
    features: [
      "Unlimited vehicles & drivers",
      "Multi-fleet / multi-branch",
      "Advanced benchmarking & rules engine",
      "API access & integrations",
      "Dedicated account manager",
      "SLA-backed support",
    ],
    cta: "Contact sales",
    featured: false,
  },
];

export default function HomePage() {
  const { user, loading } = useAuth();
  const loggedIn = !loading && user;

  return (
    <div className="min-h-screen bg-slate-100 font-sans">
      {/* ---- Top navigation ---- */}
      <header className="bg-slate-900 text-white">
        <div className="max-w-6xl mx-auto px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-sky-500 p-2 rounded-xl text-white font-black text-lg">VK</div>
            <div>
              <h1 className="text-lg font-extrabold tracking-tight leading-none">VahanKhata</h1>
              <p className="text-[11px] text-sky-400 font-medium">
                Fleet Expense Verification & Settlement Engine
              </p>
            </div>
          </div>
          <Link
            to={loggedIn ? "/dashboard" : "/login"}
            className="bg-sky-500 hover:bg-sky-600 text-white text-sm font-bold px-4 py-2 rounded-xl transition"
          >
            {loggedIn ? "Go to Dashboard" : "Login"}
{/* ---- Hero ---- */}
      <section className="bg-slate-900 text-white">
        <div className="max-w-6xl mx-auto px-5 py-16 md:py-24 text-center">
          <p className="text-sky-400 font-bold text-sm tracking-widest uppercase">
            Stop losing money to unverified fleet expenses
          </p>
          <h2 className="mt-4 text-3xl md:text-5xl font-extrabold tracking-tight leading-tight">
            Every rupee your fleet spends —<br className="hidden md:block" /> verified, benchmarked & settled
          </h2>
          <p className="mt-5 text-slate-300 max-w-2xl mx-auto text-sm md:text-base">
            VahanKhata gives fleet managers a single, real-time view of driver expenses.
            Fuel theft, overcharging and bogus claims get flagged automatically — while
            drivers get a simple WhatsApp-style way to submit receipts. No more spreadsheets,
            guesswork or payment disputes.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              to={loggedIn ? "/dashboard" : "/login"}
              className="bg-sky-500 hover:bg-sky-600 text-white font-bold px-6 py-3 rounded-xl transition"
            >
              {loggedIn ? "Open Dashboard" : "Login to VahanKhata"}
            </Link>
            <a
              href="#features"
              className="bg-slate-800 hover:bg-slate-700 text-white font-bold px-6 py-3 rounded-xl transition"
            >
              See what you get
            </a>
          </div>
          <div className="mt-10 grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-3xl mx-auto text-left">
            <div className="bg-slate-800 rounded-2xl p-4">
              <p className="text-2xl font-black text-sky-400">100%</p>
              <p className="text-xs text-slate-300 mt-1">of expenses verified with evidence</p>
            </div>
            <div className="bg-slate-800 rounded-2xl p-4">
              <p className="text-2xl font-black text-sky-400">~15%</p>
              <p className="text-xs text-slate-300 mt-1">typical reduction in fleet spend</p>
            </div>
            <div className="bg-slate-800 rounded-2xl p-4">
              <p className="text-2xl font-black text-sky-400">30 min</p>
              <p className="text-xs text-slate-300 mt-1">to set up your first fleet</p>
            </div>
          </div>
        </div>
      </section>

      {/* ---- Why / Problem ---- */}
      <section className="bg-slate-100">
        <div className="max-w-6xl mx-auto px-5 py-16">
          <h2 className="text-2xl md:text-3xl font-extrabold tracking-tight text-slate-900 text-center">
            Why fleet managers switch to VahanKhata
          </h2>
          <p className="max-w-2xl mx-auto mt-3 text-slate-600 text-center text-sm md:text-base">
            Manually logged fuel slips, cash tolls and repair bills disappear into a black box.
            You only find out at the end of the month — and by then the money is gone.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-5xl mx-auto">
            {[
              { icon: "🕳️", title: "No visibility", desc: "You can't see what drivers spend while on the road — only the total at month-end." },
              { icon: "🧾", title: "Easy to fake", desc: "Handwritten slips and cash expenses are impossible to validate honestly." },
              { icon: "⚖️", title: "Payout disputes", desc: "Drivers and managers argue over what was spent, delaying settlement and trust." },
            ].map((p) => (
              <div key={p.title} className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                <div className="text-3xl">{p.icon}</div>
                <h3 className="mt-3 font-bold text-slate-900">{p.title}</h3>
                <p className="mt-2 text-sm text-slate-600">{p.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
          </Link>
        </div>
      </header>