import React from "react";
import Seo from "../Seo";
import { PageHero, CTABand } from "../UI";
import { Button } from "../../components/ui/button.jsx";
import { Badge } from "../../components/ui/badge.jsx";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "../../components/ui/card.jsx";
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

const FAQ = [
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
      <PageHero
        eyebrow="Pricing"
        title="One plan, one price."
        lead="No hidden fees. Free trial, then a single vehicle slot — add more when you need them."
      />

      <section className="market-section market-wrap">
        <div className="grid gap-5 lg:grid-cols-3">
          {PLANS.map((p) => (
            <Card
              key={p.name}
              className={`flex flex-col ${p.highlight ? "border-primary ring-1 ring-primary" : ""}`}
            >
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{p.name}</CardTitle>
                  {p.highlight && <Badge>Most popular</Badge>}
                </div>
                <CardDescription>{p.period}</CardDescription>
              </CardHeader>
              <CardContent className="flex-1">
                <p className="text-4xl font-extrabold tracking-tight text-foreground">
                  {p.price}
                </p>
                <ul className="mt-5 space-y-2">
                  {p.features.map((f) => (
                    <li
                      key={f}
                      className="flex items-center gap-2 text-sm text-muted-foreground"
                    >
                      <span className="text-primary">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
              </CardContent>
              <CardFooter>
                <Button
                  asChild
                  className="w-full"
                  variant={p.highlight ? "default" : "outline"}
                >
                  <a href="/request-demo">Start with {p.name}</a>
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>

        <div className="mx-auto mt-16 max-w-2xl">
          <h3 className="text-center text-xl font-bold text-foreground">
            Frequently asked
          </h3>
          <Accordion type="single" collapsible className="mt-6">
            {FAQ.map(([q, a]) => (
              <AccordionItem key={q} value={q}>
                <AccordionTrigger>{q}</AccordionTrigger>
                <AccordionContent className="text-muted-foreground">
                  {a}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </section>

      <CTABand
        title="Not sure which plan fits?"
        lead="Book a free demo and we'll map the right plan to your fleet size."
      />
    </>
  );
}