import React from "react";
import Seo from "../Seo";
import { IconChip, CTABand } from "../UI";

const HERO_PAINS = [
  "Fat fuel bills with no way to catch overbilling",
  "Drivers texting receipts to a number nobody watches",
  "Driver Salery and advance arguments at settlement time",
  "Challans, repairs and cash advances lost in notebooks",
];

// Stats shown in the hero's mock "VahanKhata Dashboard" card.
const HERO_STATS = [
  { label: "Active trips", value: "1,248", cls: "bg-brand-50" },
  { label: "Expenses logged", value: "₹4.2L", cls: "bg-emerald-50" },
  { label: "Fuel saved", value: "₹38K", cls: "bg-amber-50" },
  { label: "Settled clean", value: "96%", cls: "bg-sky-50" },
];

const FEATURES = [
  ["🧾", "brand", "WhatsApp expense intake", "Drivers send fuel & receipt photos to WhatsApp. VahanKhata reads them, auto-flags overpriced or off-route fuel, and routes them for approval."],
  ["📊", "emerald", "Live fuel benchmarking", "Every petrol/DEF purchase is checked against per-state fuel bands, catching overbilling before it's paid — not at month-end."],
  ["🚚", "amber", "Trips start to settlement", "Odometer-in to Driver Salery-out. Driver consent, cash advance and salary post to the ledger automatically when a trip settles."],
  ["⚖️", "violet", "Fair Driver Salery, no disputes", "Fixed, per-km or daily Driver Salery rules make every rupee clear. Drivers see their own settlement. No more month-end arguments."],
  ["🛡️", "sky", "Emergency alerts & QR", "Every tag carries a QR and a normalized emergency alert path — with anti-spam so a stray scan never floods the inbox."],
  ["🏢", "rose", "Made for Indian fleets", "Multi-fleet, multi-manager, driver salary and Razorpay billing built in — the way Indian fleet operations actually run."],
];

function PainItem({ text, i }) {
  return (
    <li className="flex items-start gap-3">
      <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-rose-100 text-xs font-black text-rose-600">
        {i}
      </span>
      <span className="text-sm leading-relaxed text-ink-700">{text}</span>
    </li>
  );
}

const HOW = [
  ["1", "Create the trip", "Log the vehicle, driver and odometer-in. An advance posts to the ledger automatically."],
  ["2", "Driver sends expenses", "Fuel and DEF photos go to WhatsApp — read, benchmarked and flagged instantly."],
  ["3", "Manager approves", "Approve or deduct in one tap from the escalation thread. No spreadsheets."],
  ["4", "Trip settles", "Driver gives consent, Driver Salery posts, and the history locks into an auditable record."],
];

export default function Home() {
  return (
    <>
      <Seo
        title="Smart Fleet Expense & Trip Management for Indian Transport Firms"
        description="VahanKhata replaces spreadsheets and WhatsApp chaos with live fuel benchmarking, driver Driver Salery settlement and trip management — built for how Indian fleets actually run."
        path="/"
      />

      {/* HERO */}
      <section className="market-band relative overflow-hidden">
        <div className="market-grid absolute inset-0 opacity-60" aria-hidden />
        <div className="market-wrap relative grid items-center gap-10 py-16 sm:py-24 lg:grid-cols-2">
          <div>
            <span className="market-eyebrow !border-white/25 !bg-white/10 !text-brand-100">
              Built for Indian transport firms
            </span>
            <h1 className="mt-5 text-balance text-4xl font-extrabold leading-[1.05] tracking-tight text-white sm:text-5xl lg:text-[3.4rem]">
              Stop bleeding money on <span className="market-grad-text">fuel, Driver Salery and unsettled trips.</span>
            </h1>
            <p className="mt-5 max-w-xl text-pretty text-base leading-relaxed text-brand-100 sm:text-lg">
              VahanKhata turns messy WhatsApp receipts and spreadsheets into a live expense ledger — with per-state fuel
              benchmarking, driver Driver Salery settlement and full trip audit, all in the way your drivers actually work today.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <a href="/request-demo" className="market-btn market-btn-brand !bg-white !text-brand-900 hover:!bg-brand-50">
                Book a free demo
              </a>
              <a href="/pricing" className="market-btn market-btn-dark">
                See pricing
              </a>
            </div>
            <p className="mt-4 text-xs text-brand-200/80">15-day free trial · No credit card · Setup in a day</p>
          </div>

          <div className="market-card p-6">
            <div className="flex items-center gap-3 border-b border-ink-100 pb-4">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-base font-black text-white">
                F
              </span>
              <div>
                <p className="text-sm font-bold text-ink-900">VahanKhata Dashboard</p>
                <p className="text-xs text-ink-500">Live view · trips &amp; expenses</p>
              </div>
              <span className="badge badge-success ml-auto">Live</span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              {HERO_STATS.map((s) => (
                <div key={s.label} className={`rounded-xl p-4 ${s.cls}`}>
                  <p className="text-[11px] font-bold uppercase tracking-wider text-ink-500">{s.label}</p>
                  <p className="mt-1 text-2xl font-extrabold tracking-tight text-ink-900">{s.value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* PROBLEM */}
      <section className="market-section market-wrap">
        <div className="grid items-start gap-10 lg:grid-cols-2">
          <div>
            <span className="market-eyebrow">The problem</span>
            <h2 className="market-title">Fleet profits leak out in a thousand small places.</h2>
            <p className="mt-5 max-w-xl text-base leading-relaxed text-ink-600">
              Most transport firms run on WhatsApp forwards, handwritten trip sheets and a spreadsheet that's weeks
              behind. The cost of that is real — and it shows up every single month.
            </p>
          </div>
          <ul className="space-y-3">
            {HERO_PAINS.map((p, i) => (
              <PainItem key={p} text={p} i={i + 1} />
            ))}
          </ul>
        </div>
      </section>

      {/* SOLUTION: FEATURES */}
      <section className="market-section market-wrap border-t border-ink-100">
        <div className="flex flex-col items-center">
          <span className="market-eyebrow">The solution</span>
          <h2 className="market-title">Everything your fleet sends, turned into money saved.</h2>
        </div>
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(([icon, tone, title, text]) => (
            <div key={title} className="market-card-hover p-6">
              <IconChip tone={tone}>{icon}</IconChip>
              <h3 className="mt-4 text-lg font-bold text-ink-900">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-600">{text}</p>
            </div>
          ))}
        </div>
        <div className="mt-10 text-center">
          <a href="/features" className="market-btn market-btn-brand">
            Explore all features
          </a>
        </div>
      </section>

      {/* HOW IT WORKS STRIP */}
      <section className="market-section market-wrap border-t border-ink-100">
        <div className="flex flex-col items-center">
          <span className="market-eyebrow">How it works</span>
          <h2 className="market-title">From trip start to Driver Salery — on one thread.</h2>
        </div>
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {HOW.map(([n, t, d]) => (
            <div key={n} className="relative rounded-2xl border border-ink-200 bg-white p-6 shadow-sm">
              <span className="text-4xl font-black text-brand-200">{n}</span>
              <h3 className="mt-3 text-base font-bold text-ink-900">{t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-600">{d}</p>
            </div>
          ))}
        </div>
      </section>

      <CTABand />
    </>
  );
}