import React from "react";
import Seo from "../Seo";
import { Button } from "../../components/ui/button.jsx";
import { Badge } from "../../components/ui/badge.jsx";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "../../components/ui/accordion.jsx";

const PLANS = [
  {
    name: "Trial",
    price: "₹0",
    period: "15 days",
    features: ["1 vehicle", "Up to 5 drivers", "WhatsApp intake", "Fuel checks"],
    highlight: false,
  },
  {
    name: "Monthly",
    price: "₹799",
    period: "/month",
    features: ["1 vehicle incl.", "All core features", "Razorpay billing", "Email support"],
    highlight: true,
  },
  {
    name: "Yearly",
    price: "₹7,191",
    period: "/year · 25% off",
    features: ["Everything in Monthly", "Priority support", "No setup fee"],
    highlight: false,
  },
];

const FAQS = [
  ["Do drivers need to install anything?", "No — they send receipts on WhatsApp and VahanKhata reads them."],
  ["Can I add extra vehicles?", "Yes — buy extra vehicle slots any time from billing."],
  ["Will it catch overpriced fuel?", "Yes — every purchase is compared to state rates and flagged automatically."],
  ["Is there a long-term contract?", "No — start with the free trial, then go monthly or yearly."],
];

export default function Pricing() {
  return (
    <>
      <Seo
        title="Pricing"
        description="VahanKhata's simple pricing: a free 15-day trial, ₹799/month, or ₹7,191/year (25% off). No contracts, Razorpay built in."
        path="/pricing"
      />

      {/* HERO */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-3xl px-4 py-20 text-center sm:py-24 sm:px-6">
          <span className="text-xs font-semibold uppercase tracking-wider text-primary">
            Pricing
          </span>
          <h1 className="mt-6 text-4xl font-extrabold leading-tight tracking-tight text-foreground sm:text-5xl">
            One plan, one price.
          </h1>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground" lang="hi">
            एक साफ़ मूल्य, कोई छिपी शुल्लक नहीं।
          </p>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            No hidden fees. Free trial, then a single vehicle slot — add more when you need them.
          </p>
        </div>
      </section>

      {/* PLANS */}
      <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
        <div className="grid gap-5 lg:grid-cols-3">
          {PLANS.map((p) => (
            <div
              key={p.name}
              className={`flex flex-col rounded-xl border bg-card p-6 ${
                p.highlight ? "border-primary ring-1 ring-primary" : "border-border"
              }`}
            >
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-foreground">{p.name}</h3>
                {p.highlight && <Badge>Most popular</Badge>}
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{p.period}</p>
              <p className="mt-4 text-4xl font-extrabold tracking-tight text-foreground">
                {p.price}
              </p>
              <ul className="mt-5 space-y-2">
                {p.features.map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span className="text-primary">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              <Button
                asChild
                className="mt-auto"
                variant={p.highlight ? "default" : "outline"}
              >
                <a href="/request-demo">Start with {p.name}</a>
              </Button>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section className="mx-auto max-w-2xl px-4 py-16 sm:px-6">
        <h3 className="text-center text-xl font-bold text-foreground">Frequently asked</h3>
        <Accordion type="single" collapsible className="mt-6">
          {FAQS.map(([q, a]) => (
            <AccordionItem key={q} value={q}>
              <AccordionTrigger>{q}</AccordionTrigger>
              <AccordionContent className="text-muted-foreground">
                {a}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </section>

      {/* CLOSING CTA */}
      <section className="mx-auto mb-24 max-w-3xl px-4 py-16 text-center sm:px-6">
        <h2 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
          Not sure which plan fits?
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base">
          Book a free demo and we'll map the right plan to your fleet size.
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