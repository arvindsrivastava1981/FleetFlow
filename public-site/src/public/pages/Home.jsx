import React from "react";
import Seo from "../Seo";
import { Button } from "../../components/ui/button.jsx";
import { Card } from "../../components/ui/card.jsx";
import { MessageSquareText, Fuel, Scale } from "lucide-react";

const PILLARS = [
  {
    icon: MessageSquareText,
    title: "WhatsApp receipts",
    text: "Drivers send slips on WhatsApp. No app, no training, no lost receipts.",
  },
  {
    icon: Fuel,
    title: "Live fuel checks",
    text: "Every purchase compared to state rates. Overpricing flagged instantly.",
  },
  {
    icon: Scale,
    title: "Fair settlement",
    text: "Advances and salary settle into a signed PDF — automatically.",
  },
];

export default function Home() {
  return (
    <>
      <Seo
        title="Fleet Expense & Trip Management for Indian Transport"
        description="VahanKhata verifies fuel, tracks trips and settles driver salary for Indian transport firms. Trip start to settlement on WhatsApp."
        path="/"
      />

      {/* HERO */}
      <section className="border-b border-border">
        <div className="mx-auto px-4 py-20 text-center sm:py-28 sm:px-6 lg:px-8 max-w-5xl">
          <span className="text-xs font-semibold uppercase tracking-wider text-primary">
            Fleet expense &amp; trip management
          </span>
          <h1 className="mt-6 text-4xl font-extrabold leading-tight tracking-tight text-foreground sm:text-5xl lg:text-6xl">
            Every rupee your fleet spends, accounted for.
          </h1>
          <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            VahanKhata verifies fuel, tracks trips and settles driver salary —
            from dispatch to signed settlement.
          </p>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base" lang="hi">
            आपके फ्लीट का हर खर्च — पेट्रोल से लेकर ड्राइवर वेतन तक — WhatsApp पर,
            बिना किसी ऐप के। ड्राइवर रसीद भेजता है, सब कुछ अपने आप जमा और जाँच होता है।
          </p>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Button asChild size="lg">
              <a href="/request-demo">Start free trial</a>
            </Button>
            <Button asChild size="lg" variant="outline">
              <a href="/features">See how it works</a>
            </Button>
          </div>
          <p className="mt-4 text-xs text-muted-foreground">
            Free 15-day trial · No credit card · Razorpay billing
          </p>
        </div>
      </section>

      {/* THREE PILLARS */}
      <section className="mx-auto px-4 py-16 sm:px-6 lg:px-8 max-w-5xl">
        <div className="grid gap-5 sm:grid-cols-3">
          {PILLARS.map((p) => (
            <Card key={p.title} className="p-6">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <p.icon className="h-5 w-5" />
              </div>
              <h2 className="mt-4 text-base font-bold text-foreground">{p.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {p.text}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {/* CLOSING CTA */}
      <section className="mx-auto mb-24 px-4 py-16 text-center sm:px-6 lg:px-8 max-w-3xl">
        <h2 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
          Ready to take control of your fleet?
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