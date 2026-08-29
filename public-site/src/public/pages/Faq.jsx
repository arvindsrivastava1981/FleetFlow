import React from "react";
import Seo from "../Seo";
import { Button } from "../../components/ui/button.jsx";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "../../components/ui/accordion.jsx";

const FAQS = [
  [
    "Do drivers need to install an app?",
    "No. Drivers send receipts on WhatsApp and VahanKhata reads and checks them.",
  ],
  [
    "How does salary settlement work?",
    "Set each driver's rule (fixed, per-km, daily). Advances ledger at trip start; salary and consent settle at sign-off.",
  ],
  [
    "Will it catch fuel overbilling?",
    "Yes. Every petrol/DEF purchase is compared to state rates and flagged before approval.",
  ],
  [
    "We run multiple fleets. Does it scale?",
    "Yes — multi-fleet and multi-manager with role-based scoping for super admins and managers.",
  ],
  [
    "Is our data secure?",
    "Role-based access, time-limited sessions and an audit ledger on every change. Full details on the Security page.",
  ],
  [
    "How does billing and the trial work?",
    "Free 15-day trial on one vehicle. Then ₹799/month or ₹7,191/year (25% off), billed via Razorpay — add vehicle slots anytime.",
  ],
];

export default function Faq() {
  return (
    <>
      <Seo
        title="FAQ"
        description="Answers about VahanKhata: WhatsApp expense intake, driver salary settlement, fuel benchmarking, security, multi-fleet support and billing."
        path="/faq"
      />

      {/* HERO */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-3xl px-4 py-20 text-center sm:py-24 sm:px-6">
          <span className="text-xs font-semibold uppercase tracking-wider text-primary">
            FAQ
          </span>
          <h1 className="mt-6 text-4xl font-extrabold leading-tight tracking-tight text-foreground sm:text-5xl">
            Questions, answered.
          </h1>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground" lang="hi">
            आपके सवालों के छोटे‑छोटे जवाब।
          </p>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            Short answers to the things fleet owners ask us most.
          </p>
        </div>
      </section>

      {/* FAQS */}
      <section className="mx-auto max-w-2xl px-4 py-16 sm:px-6">
        <Accordion type="single" collapsible>
          {FAQS.map(([q, a]) => (
            <AccordionItem key={q} value={q}>
              <AccordionTrigger>{q}</AccordionTrigger>
              <AccordionContent className="text-muted-foreground">
                {a}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
        <div className="mt-10 text-center">
          <Button asChild>
            <a href="/contact">Ask us directly</a>
          </Button>
        </div>
      </section>

      {/* CLOSING CTA */}
      <section className="mx-auto mb-24 max-w-3xl px-4 py-16 text-center sm:px-6">
        <h2 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
          Still got questions?
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base">
          Book a free demo — see the full trip-to-settlement flow without a spreadsheet.
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