import React from "react";
import Seo from "../Seo";
import { PageHero, CTABand, IconChip } from "../UI";
import { ClipboardCheck, Handshake, Radar } from "lucide-react";

const VALUES = [
  {
    icon: ClipboardCheck,
    title: "Clarity over chaos",
    text: "Every trip, litre and rupee on a live, honest ledger.",
  },
  {
    icon: Handshake,
    title: "Fair to drivers",
    text: "Clean salary and settlement build the trust that keeps drivers.",
  },
  {
    icon: Radar,
    title: "Zero silent leakage",
    text: "Overpriced fuel and lost slips are caught first, not last.",
  },
];

export default function About() {
  return (
    <>
      <Seo
        title="About Us"
        description="VahanKhata gives Indian transport firms one honest view of every trip — from fuel to salary settlement."
        path="/about"
      />
      <PageHero
        eyebrow="Our mission"
        title="Every rupee accounted for. Every driver treated fairly."
        lead="Indian transport runs on trust. VahanKhata gives that trust a record."
      />

      <section className="market-section market-wrap">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-lg leading-relaxed text-muted-foreground">
            Unchecked WhatsApp receipts and handwritten ledgers were eating
            firms' margins. VahanKhata joins the WhatsApp drivers already use
            to strict fuel benchmarking — so owners earn more and drivers get a
            fair deal.
          </p>
        </div>
        <div className="mx-auto mt-12 grid max-w-3xl gap-5 sm:grid-cols-3">
          {VALUES.map((v) => (
            <div
              key={v.title}
              className="flex flex-col items-center rounded-xl border border-border bg-card p-6 text-center"
            >
              <IconChip>
                <v.icon className="h-5 w-5" />
              </IconChip>
              <h3 className="mt-4 text-base font-bold text-foreground">{v.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {v.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      <CTABand title="Let's build cleaner fleets together." />
    </>
  );
}