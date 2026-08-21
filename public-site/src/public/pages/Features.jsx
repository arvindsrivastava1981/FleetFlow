import React from "react";
import Seo from "../Seo";
import { PageHero, CTABand } from "../UI";

const GROUPS = [
  {
    title: "Trip management",
    icon: "🚚",
    items: [
      "Start, complete and settle trips with odometer tracking",
      "Auto-generated trip codes per vehicle",
      "Operating state derived from the vehicle plate",
      "Driver assignment & consent at settlement",
    ],
  },
  {
    title: "Expense & fuel control",
    icon: "📊",
    items: [
      "WhatsApp receipt intake straight from drivers",
      "Per-state fuel & DEF benchmarking with live rate sync",
      "Automatic flagging for overpriced or off-route fuel",
      "Approve or deduct in one tap from an escalation thread",
    ],
  },
  {
    title: "Driver batta & salary",
    icon: "⚖️",
    items: [
      "Fixed, per-km, daily or none — configurable batta profiles",
      "Cash advance auto-posted at trip creation",
      "Batta & salary post to the ledger on settlement",
      "Drivers see their own clear settlement view",
    ],
  },
  {
    title: "Safety & alerts",
    icon: "🛡️",
    items: [
      "QR tags with a normalized emergency alert path",
      "Anti-spam so stray scans never flood the inbox",
      "Driver consent recorded for audit",
    ],
  },
  {
    title: "Fleet & users",
    icon: "🏢",
    items: [
      "Multi-fleet & multi-manager with role-based access",
      "Vehicles, drivers and benchmark profiles per firm",
      "Super-admin vs trip-manager scoped views",
    ],
  },
  {
    title: "Billing & reports",
    icon: "💳",
    items: [
      "Razorpay subscriptions & fleet billing",
      "Settled-trip and driver salary reports as PDF",
      "Audit ledger of every entitlement change",
    ],
  },
];

export default function Features() {
  return (
    <>
      <Seo
        title="Features — Fleet & Trip Management Platform"
        description="Explore VahanKhata's features: WhatsApp expense intake, per-state fuel benchmarking, driver batta settlement, trip management, emergency alerts, and Razorpay billing."
        path="/features"
      />
      <PageHero
        eyebrow="Features"
        title="One platform, every rupee on the road accounted for."
        lead="From the moment a driver sends a receipt to the day a trip settles, VahanKhata keeps every step tracked, benchmarked and fair."
      />

      <section className="market-section market-wrap">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {GROUPS.map((g) => (
            <div key={g.title} className="market-card-hover p-6">
              <span className="text-2xl">{g.icon}</span>
              <h3 className="mt-3 text-lg font-bold text-ink-900">{g.title}</h3>
              <ul className="mt-3 space-y-2">
                {g.items.map((it) => (
                  <li key={it} className="flex items-start gap-2 text-sm leading-relaxed text-ink-600">
                    <span className="mt-0.5 text-brand-600">✓</span>
                    {it}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-12 text-center">
          <a href="/pricing" className="market-btn market-btn-brand">
            See pricing
          </a>
        </div>
      </section>

      <CTABand />
    </>
  );
}