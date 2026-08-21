import React, { useState } from "react";
import Seo from "../Seo";
import { PageHero, CTABand } from "../UI";

const FAQS = [
  {
    q: "Do drivers need to install an app?",
    a: "No. Drivers send fuel and receipt photos straight to WhatsApp. VahanKhata reads the message, runs fuel benchmarking, and routes it for approval — no driver training or logins needed.",
  },
  {
    q: "How does Driver Salery settlement actually work?",
    a: "You set a Driver Salery profile (fixed, per-km, daily or none) per driver. When a trip is created, the cash advance posts automatically; at settlement the driver gives consent and the Driver Salery & salary post to the ledger, producing a clear, auditable record.",
  },
  {
    q: "Will it catch fuel overbilling?",
    a: "Yes. Every petrol/DEF purchase is compared against per-state fuel bands (with live rate sync). Anything above the band is auto-flagged and held for manager approval, instead of silently draining the month's margin.",
  },
  {
    q: "We run multiple branches / fleets. Does it scale?",
    a: "VahanKhata supports multi-fleet and multi-manager operations with role-based access, so super-admins see everything while each trip manager sees only their own firm's trips, vehicles and drivers.",
  },
  {
    q: "Is our data secure?",
    a: "Access is gated per role, sessions are time-limited, and every entitlement and settlement change is written to an audit ledger. See our Security page for details.",
  },
  {
    q: "How does billing and trial work?",
    a: "Start with a free 15-day trial on one vehicle. Move to Monthly (₹799) or Yearly (₹7,191 — 25% off), with Razorpay billing and the option to add extra vehicle slots whenever you need them.",
  },
  {
    q: "Can drivers see their own earnings?",
    a: "Yes. Drivers have a read-only salary/Driver Salery view and their own settled-trip receipts, which builds trust and cuts settlement disputes.",
  },
];

function FaqItem({ q, a, open, onToggle }) {
  return (
    <div className="market-card overflow-hidden">
      <button
        className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
        onClick={onToggle}
        aria-expanded={open}
      >
        <span className="font-semibold text-ink-900">{q}</span>
        <span className={`text-lg text-brand-600 transition-transform ${open ? "rotate-45" : ""}`}>+</span>
      </button>
      {open && <p className="px-5 pb-5 text-sm leading-relaxed text-ink-600">{a}</p>}
    </div>
  );
}

export default function Faq() {
  const [open, setOpen] = useState(null);
  return (
    <>
      <Seo
        title="FAQ"
        description="Answers to common questions about VahanKhata: WhatsApp expense intake, Driver Salery settlement, fuel benchmarking, security, multi-fleet support and billing."
        path="/faq"
      />
      <PageHero
        eyebrow="FAQ"
        title="Questions, answered."
        lead="Everything fleet owners and managers ask us, in plain language. Still curious? Contact our team."
      />

      <section className="market-section market-wrap">
        <div className="mx-auto max-w-2xl space-y-3">
          {FAQS.map((f, i) => (
            <FaqItem
              key={f.q}
              q={f.q}
              a={f.a}
              open={open === i}
              onToggle={() => setOpen(open === i ? null : i)}
            />
          ))}
        </div>
        <div className="mt-10 text-center">
          <a href="/contact" className="market-btn market-btn-brand">
            Ask us directly
          </a>
        </div>
      </section>

      <CTABand />
    </>
  );
}