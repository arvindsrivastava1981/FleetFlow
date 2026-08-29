import React from "react";
import Seo from "../Seo";
import { Button } from "../../components/ui/button.jsx";
import { Check } from "lucide-react";

const FEATURES = [
  "1 vehicle slot (add more anytime)",
  "WhatsApp receipt intake",
  "Live fuel rate checks",
  "Auto driver settlement PDF",
  "Email support",
];

export default function Pricing() {
  return (
    <>
      <Seo
        title="Pricing"
        description="VahanKhata's simple pricing: a free 15-day trial, ₹799/month, or ₹7,191/year (25% off). No contracts, Razorpay built in."
        path="/pricing"
      />

      <section className="border-b border-border">
        <div className="mx-auto max-w-3xl px-4 py-20 text-center sm:py-24 sm:px-6">
          <span className="text-xs font-semibold uppercase tracking-wider text-primary">
            Pricing
          </span>
          <h1 className="mt-6 text-4xl font-extrabold leading-tight tracking-tight text-foreground sm:text-5xl">
            One plan, one price.
          </h1>
          <p className="mt-2 text-sm text-muted-foreground" lang="hi">
            एक साफ़ मूल्य, कोई छिपी शुल्क नहीं।
          </p>
        </div>
      </section>

      <section className="mx-auto max-w-md px-4 py-16 sm:px-6">
        <div className="rounded-2xl border border-primary bg-card p-8 shadow-sm ring-1 ring-primary">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-foreground">Monthly</h2>
            <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
              ₹7,191/yr · 25% off
            </span>
          </div>
          <p className="mt-4 text-5xl font-extrabold tracking-tight text-foreground">
            ₹799
            <span className="text-base font-medium text-muted-foreground"> /month</span>
          </p>
          <p className="mt-1 text-xs text-muted-foreground">After the free 15-day trial</p>
          <ul className="mt-6 space-y-2.5">
            {FEATURES.map((f) => (
              <li key={f} className="flex items-center gap-2 text-sm text-muted-foreground">
                <Check className="h-4 w-4 text-primary" aria-hidden="true" />
                {f}
              </li>
            ))}
          </ul>
          <Button asChild size="lg" className="mt-8 w-full">
            <a href="/request-demo">Start free trial</a>
          </Button>
        </div>
        <p className="mt-6 text-center text-xs text-muted-foreground">
          No contracts · Razorpay billing · Cancel anytime
        </p>
      </section>
    </>
  );
}