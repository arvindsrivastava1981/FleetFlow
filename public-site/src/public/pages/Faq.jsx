import React from "react";
import Seo from "../Seo";
import { PageHero, CTABand } from "../UI";
import { Button } from "../../components/ui/button.jsx";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "../../components/ui/accordion.jsx";

const FAQS = [
  ["Do drivers need to install an app?", "No. Drivers send receipts on WhatsApp and VahanKhata reads and checks them."],
  ["How does salary settlement work?", "Set each driver's rule (fixed, per-km, daily). Advances ledger at trip start; salary and consent settle at sign-off."],
  ["Will it catch fuel overbilling?", "Yes. Every petrol/DEF purchase is compared to state rates and flagged before approval."],
  ["We run multiple fleets. Does it scale?", "Yes — multi-fleet and multi-manager with role-based scoping for super admins and managers."],
  ["Is our data secure?", "Role-based access, time-limited sessions and an audit ledger on every change. Full details on the Security page."],
  ["How does billing and the trial work?", "Free 15-day trial on one vehicle. Then ₹799/month or ₹7,191/year (25% off), billed via Razorpay — add vehicle slots anytime."],
];

export default function Faq() {
  return (
    <>
      <Seo
        title="FAQ"
        description="Answers about VahanKhata: WhatsApp expense intake, driver salary settlement, fuel benchmarking, security, multi-fleet support and billing."
        path="/faq"
      />
      <PageHero
        eyebrow="FAQ"
        title="Questions, answered."
        lead="Short answers to the things fleet owners ask us most."
      />

      <section className="market-section market-wrap">
        <div className="mx-auto max-w-2xl">
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
        </div>
        <div className="mt-10 text-center">
          <Button asChild>
            <a href="/contact">Ask us directly</a>
          </Button>
        </div>
      </section>

      <CTABand />
    </>
  );
}