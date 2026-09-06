import React from "react";
import Seo from "../Seo";
import { Button } from "../../components/ui/button.jsx";
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
    text: "Drivers send receipts on WhatsApp. VahanKhata.in reads and checks them.",
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
        description="VahanKhata.in features: WhatsApp expense intake, per-state fuel benchmarking, driver salary settlement, automatic fraud checks and Razorpay billing."
        path="/features"
      />

      {/* HERO */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-3xl px-4 py-20 text-center sm:py-24 sm:px-6">
          <span className="text-xs font-semibold uppercase tracking-wider text-primary">
            Features
          </span>
          <h1 className="mt-6 text-4xl font-extrabold leading-tight tracking-tight text-foreground sm:text-5xl">
            Everything on the road, accounted for.
          </h1>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground" lang="hi">
            ड्राइवर के रसीद़ से लेकर साइन‑ऑफ़ तक — एक साफ़ रिकॉर्ड।
          </p>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            From the driver's receipt to the signed settlement — tracked,
            benchmarked and clean.
          </p>
        </div>
      </section>

      {/* FEATURES */}
      <section className="mx-auto max-w-4xl px-4 py-16 sm:px-6">
        <div className="grid gap-x-8 gap-y-6 sm:grid-cols-2">
          {FEATURES.map((f) => (
            <div key={f.title} className="flex items-start gap-3">
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <f.icon className="h-4 w-4" aria-hidden="true" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-foreground">{f.title}</h3>
                <p className="mt-0.5 text-sm text-muted-foreground">{f.text}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-12 text-center">
          <Button asChild size="lg">
            <a href="/request-demo">Start free trial</a>
          </Button>
        </div>
      </section>
    </>
  );
}