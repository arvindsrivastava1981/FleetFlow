import React from "react";
import Seo from "../Seo";
import { Button } from "../../components/ui/button.jsx";
import { Card } from "../../components/ui/card.jsx";
import { ClipboardCheck, Handshake, Radar } from "lucide-react";

const VALUES = [
  {
    icon: ClipboardCheck,
    title: "Clarity over chaos",
    text: "Every trip, litre and rupee on a live, honest ledger.",
  },
  {
    icon: Handshake,
    title: "Fair to drivers",
    text: "Clean salary and settlement build the trust that keeps drivers.",
  },
  {
    icon: Radar,
    title: "Zero silent leakage",
    text: "Overpriced fuel and lost slips are caught first, not last.",
  },
];

export default function About() {
  return (
    <>
      <Seo
        title="About Us"
        description="VahanKhata gives Indian transport firms one honest view of every trip — from fuel to salary settlement."
        path="/about"
      />

      {/* HERO */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-3xl px-4 py-20 text-center sm:py-24 sm:px-6">
          <span className="text-xs font-semibold uppercase tracking-wider text-primary">
            Our mission
          </span>
          <h1 className="mt-6 text-4xl font-extrabold leading-tight tracking-tight text-foreground sm:text-5xl">
            Every rupee accounted for. Every driver treated fairly.
          </h1>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
            भारतीय ट्रांसपोर्ट वहां चलता है जहाँ भरोसा सबसे पहले होता है —
            वहाँखाता उस भरोसे का एक साफ़ रिकॉर्ड रखता है।
          </p>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            Indian transport runs on trust. VahanKhata gives that trust a record.
          </p>
        </div>
      </section>

      {/* STORY */}
      <section className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <p className="text-base leading-relaxed text-muted-foreground">
          Unchecked WhatsApp receipts and handwritten ledgers were eating
          firms' margins. VahanKhata joins the WhatsApp drivers already use
          to strict fuel benchmarking — so owners earn more and drivers get a
          fair deal.
        </p>
      </section>

      {/* VALUES */}
      <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
        <div className="grid gap-5 sm:grid-cols-3">
          {VALUES.map((v) => (
            <Card key={v.title} className="p-6 text-center">
              <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <v.icon className="h-5 w-5" />
              </div>
              <h3 className="mt-4 text-base font-bold text-foreground">{v.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {v.text}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {/* CLOSING CTA */}
      <section className="mx-auto mb-24 max-w-3xl px-4 py-16 text-center sm:px-6">
        <h2 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
          Let's build cleaner fleets together.
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base">
          Book a free demo — see the full trip-to-settlement flow today.
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