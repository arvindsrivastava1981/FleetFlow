import React from "react";
import Seo from "../Seo";
import { PageHero, CTABand, IconChip } from "../UI";

const REASONS = [
  ["📊", "Per-state fuel benchmarking", "Most tools just record what drivers spend. FleetFlow compares every petrol purchase to per-state bands, so overpriced fuel is flagged the moment it's submitted — not caught at audit."],
  ["💬", "WhatsApp the drivers already use", "No app to install, no training. Drivers send receipt photos to a number; FleetFlow reads, benchmarks and routes them. Adoption happens in days, not months."],
  ["⚖️", "Batta without battles", "Fixed, per-km or daily batta rules automate settlement. Drivers see their own numbers and consent digitally — ending the month-end arguments that cost you time and freight."],
  ["🧾", "Cash advances stay traceable", "Advances post to the ledger automatically at trip creation and reconcile on settlement — no more 'who has what' uncertainty."],
  ["🛡️", "Emergency alerts that actually route", "Every tag carries a QR and a normalized emergency path, with anti-spam. A real incident reaches the right person in one tap."],
  ["🏢", "Scales with your firm", "Own one fleet or a multi-branch operation — multi-fleet and multi-manager support, with Razorpay billing built in."],
];

export default function WhyUs() {
  return (
    <>
      <Seo
        title="Why FleetFlow — Compared to Spreadsheets & Other Fleet Tools"
        description="See why transport firms choose FleetFlow over spreadsheets and ERP-style fleet software: live fuel benchmarking, WhatsApp intake, fair batta and a full audit trail."
        path="/why-us"
      />
      <PageHero
        eyebrow="Why FleetFlow"
        title="Spreadsheets didn't scale. Neither will a heavyweight ERP."
        lead="FleetFlow sits in the sweet spot — the WhatsApp workflow your drivers know, with the airtight accounting and benchmarking your margins demand."
      />

      <section className="market-section market-wrap">
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {REASONS.map(([icon, title, text]) => (
            <div key={title} className="market-card-hover p-6">
              <IconChip>{icon}</IconChip>
              <h3 className="mt-4 text-lg font-bold text-ink-900">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-600">{text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* COMPARISON */}
      <section className="market-section market-wrap border-t border-ink-100">
        <div className="flex flex-col items-center">
          <span className="market-eyebrow">Side by side</span>
          <h2 className="market-title">Where FleetFlow wins.</h2>
        </div>
        <div className="market-card mt-12 overflow-hidden">
          <div className="hidden grid-cols-3 border-b border-ink-200 bg-ink-50 px-6 py-3 text-sm font-bold text-ink-700 sm:grid">
            <span className="col-span-2">Capability</span>
            <span className="text-brand-600">FleetFlow</span>
          </div>
          {[
            ["Live fuel benchmarking, not month-end shocks", "✅"],
            ["Drivers input via WhatsApp — zero training", "✅"],
            ["Automated batta & advance settlement", "✅"],
            ["Full audit trail from trip start to settle", "✅"],
            ["Built for Indian fleet operations & billing", "✅"],
          ].map(([text, mark]) => (
            <div key={text} className="grid grid-cols-3 gap-2 border-b border-ink-100 px-6 py-4 text-sm last:border-b-0">
              <span className="col-span-2 text-ink-700">{text}</span>
              <span className="font-bold text-emerald-600">{mark}</span>
            </div>
          ))}
        </div>
        <div className="mt-8 text-center">
          <a href="/request-demo" className="market-btn market-btn-brand">
            See it on a live demo
          </a>
        </div>
      </section>

      <CTABand />
    </>
  );
}