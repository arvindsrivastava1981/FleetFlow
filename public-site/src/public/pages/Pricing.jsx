import React from "react";
import Seo from "../Seo";
import { PageHero, CTABand } from "../UI";
import { FuelLeak } from "../Illustrations";

const PLANS = [
  {
    name: "Trial",
    tagline: "एक गाड़ी पर खुद देखें — मुफ़्त।",
    price: "₹0",
    period: "15 days",
    features: ["1 vehicle", "Up to 5 drivers", "WhatsApp expense intake", "Fuel benchmarking"],
    highlight: false,
  },
  {
    name: "Monthly",
    tagline: "बढ़ती फ्लीट के लिए।",
    price: "₹799",
    period: "/month",
    features: ["1 vehicle included", "All core features", "Razorpay billing", "Email support"],
    highlight: true,
  },
  {
    name: "Yearly",
    tagline: "सबसे बढ़िया डील — 25% छूट।",
    price: "₹7,191",
    period: "/year",
    features: ["1 vehicle included", "Everything in Monthly", "Priority support", "No setup fee"],
    highlight: false,
  },
];

const FAQ = [
  ["Can I add extra vehicles? · गाड़ी बढ़ा सकते हैं?", "हाँ — billing से कभी भी एक्स्ट्रा व्हीकल स्लॉट खरीदें।"],
  ["Do drivers need to install anything? · ड्राइवर को कुछ चाहिए?", "नहीं — रसीदें WhatsApp पर; VahanKhata खुद पढ़ लेता है।"],
  ["Is there a long-term contract? · कोई लंबा ठेका?", "नहीं — 15 दिन फ्री ट्रायल से शुरू करें, जब चाहें Monthly/Yearly लें।"],
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
        eyebrow="Pricing · कीमत"
        title="Plans that fit how you run."
        lead="15 दिन फ्री। एक प्लान, एक कीमत — कोई छुपा शुल्क नहीं, ज़रूरत पर एक्स्ट्रा गाड़ी स्लॉट।"
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

        <div className="mt-14 grid items-center gap-8 lg:grid-cols-2">
          <FuelLeak className="w-full rounded-3xl shadow-pop" />
          <div>
            <h3 className="text-xl font-bold text-ink-900">Catch overpriced fuel the moment it happens.</h3>
            <p className="mt-2 text-base leading-relaxed text-ink-600">
              ज़्यादा दाम वाला ईंधन उसी वक़्त फ्लैग — महीने के आखि़ में झटका नहीं।
            </p>
            <a href="/features" className="market-btn market-btn-brand mt-4">
              See how · ऐसे काम करता है
            </a>
          </div>
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