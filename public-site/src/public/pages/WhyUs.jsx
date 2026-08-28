import React from "react";
import Seo from "../Seo";
import { PageHero, CTABand, IconChip } from "../UI";
import { Fuel, MessagesSquare, Scale } from "lucide-react";

const REASONS = [
  {
    icon: Fuel,
    title: "Live fuel checks",
    text: "Other tools only log spends. VahanKhata checks every petrol purchase against state rates and flags the difference.",
  },
  {
    icon: MessagesSquare,
    title: "WhatsApp, not training",
    text: "Drivers use the app they already have. Adoption starts in days, not months.",
  },
  {
    icon: Scale,
    title: "Settlements without rows",
    text: "Advances and salary settle on a transparent, signed record — no monthly fights.",
  },
];

export default function WhyUs() {
  return (
    <>
      <Seo
        title="Why VahanKhata"
        description="Why transport firms choose VahanKhata over spreadsheets and ERP fleet tools: live fuel checks, WhatsApp intake and fair driver settlement."
        path="/why-us"
      />
      <PageHero
        eyebrow="Why VahanKhata"
        title="Spreadsheets lost the money. So did heavy ERPs."
        lead="The WhatsApp your drivers already use, joined to a ledger your owners can trust."
      />

      <section className="market-section market-wrap">
        <div className="grid gap-5 sm:grid-cols-3">
          {REASONS.map((r) => (
            <div
              key={r.title}
              className="rounded-xl border border-border bg-card p-6"
            >
              <IconChip>
                <r.icon className="h-5 w-5" />
              </IconChip>
              <h3 className="mt-4 text-base font-bold text-foreground">{r.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {r.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      <CTABand
        title="See the difference on a live demo."
        lead="Fifteen minutes, your fleet, your numbers."
        ctaText="Book a demo"
        ctaHref="/request-demo"
      />
    </>
  );
}