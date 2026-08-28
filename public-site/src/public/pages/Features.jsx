import React from "react";
import Seo from "../Seo";
import { PageHero, CTABand, IconChip } from "../UI";
import {
  MessagesSquare,
  Gauge,
  Scale,
  ShieldCheck,
  Building2,
  FileText,
} from "lucide-react";

const FEATURES = [
  {
    icon: MessagesSquare,
    title: "WhatsApp receipt intake",
    text: "Drivers send receipts on WhatsApp. VahanKhata reads and checks them.",
  },
  {
    icon: Gauge,
    title: "Live fuel benchmarking",
    text: "Every petrol & DEF purchase compared to per-state rates.",
  },
  {
    icon: Scale,
    title: "Driver salary settlement",
    text: "Fixed, per-km or daily rules settle automatically at sign-off.",
  },
  {
    icon: ShieldCheck,
    title: "Automatic fraud checks",
    text: "Overfill, mileage drops and cash tolls get flagged before settlement.",
  },
  {
    icon: Building2,
    title: "Multi-fleet & roles",
    text: "Super-admin and manager scoping for firms with many branches.",
  },
  {
    icon: FileText,
    title: "Signed PDF reports",
    text: "Every settled trip ships with a verifiable, signed record.",
  },
];

export default function Features() {
  return (
    <>
      <Seo
        title="Features"
        description="VahanKhata features: WhatsApp expense intake, per-state fuel benchmarking, driver salary settlement, automatic fraud checks and Razorpay billing."
        path="/features"
      />
      <PageHero
        eyebrow="Features"
        title="Everything on the road, accounted for."
        lead="From the driver's receipt to the signed settlement — tracked, benchmarked and clean."
      />

      <section className="market-section market-wrap">
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="rounded-xl border border-border bg-card p-6"
            >
              <IconChip>
                <f.icon className="h-5 w-5" />
              </IconChip>
              <h3 className="mt-4 text-base font-bold text-foreground">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {f.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      <CTABand
        title="See it on your fleet."
        lead="Book a free demo and we'll map the right setup to your vehicles and drivers."
        ctaText="Book a demo"
        ctaHref="/request-demo"
      />
    </>
  );
}