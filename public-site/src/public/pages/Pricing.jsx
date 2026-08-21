import React from "react";
import Seo from "../Seo";
import { PageHero, CTABand } from "../UI";

const PLANS = [
  {
    name: "Trial",
    tagline: "See it work on one vehicle — free.",
    price: "₹0",
    period: "15 days",
    features: ["1 vehicle", "Up to 5 drivers", "WhatsApp expense intake", "Fuel benchmarking"],
    highlight: false,
  },
  {
    name: "Monthly",
    tagline: "For growing single-vehicle fleets.",
    price: "₹799",
    period: "/month",
    features: ["1 vehicle included", "All core features", "Razorpay billing", "Email support"],
    highlight: true,
  },
  {
    name: "Yearly",
    tagline: "Best value, 25% off.",
    price: "₹7,191",
    period: "/year",
    features: ["1 vehicle included", "Everything in Monthly", "Priority support", "No setup fee"],
    highlight: false,
  },
];

const FAQ = [
  ["Can I add extra vehicles?", "Yes — extra vehicle slots can be purchased per firm directly from billing."],
  ["Do drivers need to install anything?", "No. Drivers send receipts via WhatsApp; VahanKhata reads them."],
  ["Is there a long-term contract?", "No. Start on the free 15-day Trial, move to Monthly or Yearly when you're ready."],
];

export default function Pricing() {
  return (
    <>
      <Seo
        title="Pricing — Transparent Fleet Management Plans"
        description="VahanKhata's simple pricing: a free 15-day trial, ₹799/month per vehicle, or ₹7,191/year (25% off). No long contracts, Razorpay billing built in."
        path="/pricing"
      />
      <PageHero
        eyebrow="Pricing"
        title="Plans that fit how you run."
        lead="Start free for 15 days. Scale to one plan, one price — no per-seat surprises, extra vehicle slots whenever you need them."
      />

      <section className="market-section market-wrap">
        <div className="grid gap-6 lg:grid-cols-3">
          {PLANS.map((p) => (
            <div
              key={p.name}
              className={`market-card-hover relative flex flex-col p-6 ${
                p.highlight ? "market-band !border-0 !shadow-xl" : ""
              }`}
            >
              {p.highlight && (
                <span className="badge badge-success absolute right-4 top-4">Most popular</span>
              )}
              <h3 className={`text-lg font-extrabold ${p.highlight ? "text-white" : "text-ink-900"}`}>{p.name}</h3>
              <p className={`mt-1 text-sm ${p.highlight ? "text-brand-100" : "text-ink-500"}`}>{p.tagline}</p>
              <div className="mt-6 flex items-baseline gap-1">
                <span className={`text-4xl font-black tracking-tight ${p.highlight ? "text-white" : "text-ink-900"}`}>
                  {p.price}
                </span>
                <span className={`text-sm font-semibold ${p.highlight ? "text-brand-100" : "text-ink-500"}`}>
                  {p.period}
                </span>
              </div>
              <ul className="mt-6 flex-1 space-y-3">
                {p.features.map((f) => (
                  <li key={f} className={`flex items-center gap-2 text-sm ${p.highlight ? "text-brand-50" : "text-ink-700"}`}>
                    <span className={p.highlight ? "text-emerald-300" : "text-emerald-600"}>✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              <a
                href="/request-demo"
                className={`mt-8 w-full market-btn ${
                  p.highlight ? "market-btn-brand !bg-white !text-brand-900 hover:!bg-brand-50" : "market-btn-ghost"
                }`}
              >
                Start with {p.name}
              </a>
            </div>
          ))}
        </div>

        <div className="mx-auto mt-14 max-w-2xl">
          <h3 className="text-center text-xl font-bold text-ink-900">Frequently asked</h3>
          <div className="mt-6 space-y-4">
            {FAQ.map(([q, a]) => (
              <div key={q} className="market-card p-5">
                <p className="font-semibold text-ink-900">{q}</p>
                <p className="mt-1 text-sm leading-relaxed text-ink-600">{a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <CTABand title="Not sure which plan fits?" lead="Book a free demo and we'll map the right plan to your fleet size." />
    </>
  );
}