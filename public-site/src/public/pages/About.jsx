import React from "react";
import Seo from "../Seo";
import { PageHero, CTABand, IconChip } from "../UI";

const VALUES = [
  ["🎯", "Clarity over chaos", "Fleet owners shouldn't guess where money went. One live ledger for every trip, litre and rupee."],
  ["⚖️", "Fairness for drivers", "Transparent batta and settlement means drivers trust the system — and stay."],
  ["📉", "Stop silent leakage", "Fuel overbilling and lost chalans are costs hiding in plain sight. We surface them first."],
  ["🚚", "Built for the road", "WhatsApp-first input, made for drivers on the highway, not office desktops."],
];

export default function About() {
  return (
    <>
      <Seo
        title="About Us"
        description="VahanKhata exists to give Indian transport firms a single, honest view of every trip — from fuel to batta settlement. Meet the team and mission."
        path="/about"
      />
      <PageHero
        eyebrow="Our story"
        title="We live where the fleet does."
        lead="VahanKhata was built after watching transport firms lose profit to untracked WhatsApp receipts, handwritten trip sheets and month-end settlement battles."
      />

      {/* MISSION */}
      <section className="market-section market-wrap">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <div>
            <span className="market-eyebrow">Our mission</span>
            <h2 className="market-title">Every rupee accounted for. Every driver treated fairly.</h2>
            <p className="mt-5 text-base leading-relaxed text-ink-600">
              Transport firms in India run on trust and relationships. We want to give that trust a record. VahanKhata
              pairs driver-friendly WhatsApp intake with hard-nosed fuel benchmarking and batta settlement, so owners
              see margins rise while drivers see a fairer, clearer deal.
            </p>
            <p className="mt-4 text-base leading-relaxed text-ink-600">
              We are builders, logistic folks and designers who believe the answer to fleet chaos isn't a heavier ERP —
              it's the tool your drivers already use: WhatsApp, made accountable.
            </p>
          </div>
          <div className="market-card p-6">
            <div className="grid grid-cols-2 gap-4">
              {[
                { k: "1", v: "WhatsApp-first" },
                { k: "50+", v: "fuel benchmarks" },
                { k: "0", v: "spreadsheets needed" },
                { k: "360", v: "degrees audit trail" },
              ].map((s) => (
                <div key={s.v} className="rounded-xl bg-ink-50 p-4 text-center">
                  <p className="text-3xl font-black text-brand-600">{s.k}</p>
                  <p className="mt-1 text-xs font-semibold text-ink-500">{s.v}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* VALUES */}
      <section className="market-section market-wrap border-t border-ink-100">
        <div className="flex flex-col items-center">
          <span className="market-eyebrow">What we stand for</span>
          <h2 className="market-title">Values that drive every build.</h2>
        </div>
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {VALUES.map(([icon, title, text]) => (
            <div key={title} className="market-card-hover p-6">
              <IconChip>{icon}</IconChip>
              <h3 className="mt-4 text-base font-bold text-ink-900">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-600">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <CTABand title="Let's build cleaner fleets together." />
    </>
  );
}