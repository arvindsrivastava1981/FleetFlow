import React from "react";
import Seo from "../Seo";
import { Button } from "../../components/ui/button.jsx";
import { Card } from "../../components/ui/card.jsx";
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

      {/* HERO */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-3xl px-4 py-20 text-center sm:py-24 sm:px-6">
          <span className="text-xs font-semibold uppercase tracking-wider text-primary">
            Features
          </span>
          <h1 className="mt-6 text-4xl font-extrabold leading-tight tracking-tight text-foreground sm:text-5xl">
            Everything on the road, accounted for.
          </h1>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
            ड्राइवर के रसीद़ से लेकर साइन‑ऑफ़ तक — एक साफ़ रिकॉर्ड।
          </p>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            From the driver's receipt to the signed settlement — tracked,
            benchmarked and clean.
          </p>
        </div>
      </section>

      {/* FEATURES */}
      <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <Card key={f.title} className="p-6">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <f.icon className="h-5 w-5" />
              </div>
              <h3 className="mt-4 text-base font-bold text-foreground">{f.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {f.text}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {/* CLOSING CTA */}
      <section className="mx-auto mb-24 max-w-3xl px-4 py-16 text-center sm:px-6">
        <h2 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
          See it on your fleet.
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base">
          Book a free demo and we'll map the right setup to your vehicles and drivers.
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Button asChild size="lg">
            <a href="/request-demo">Book a demo</a>
          </Button>
          <Button asChild size="lg" variant="outline">
            <a href="/">Log in</a>
          </Button>
        </div>
      </section>
    </>
  );
}