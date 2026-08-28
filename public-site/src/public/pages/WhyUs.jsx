import React from "react";
import Seo from "../Seo";
import { Button } from "../../components/ui/button.jsx";
import { Card } from "../../components/ui/card.jsx";
import { Fuel, MessagesSquare, Scale } from "lucide-react";

const REASONS = [
  {
    icon: Fuel,
    title: "Live fuel checks",
    text: "Other tools only log spends. VahanKhata checks every petrol purchase against state rates and flags the difference.",
  },
  {
    icon: MessagesSquare,
    title: "WhatsApp, not training",
    text: "Drivers use the app they already have. Adoption starts in days, not months.",
  },
  {
    icon: Scale,
    title: "Settlements without rows",
    text: "Advances and salary settle on a transparent, signed record — no monthly fights.",
  },
];

export default function WhyUs() {
  return (
    <>
      <Seo
        title="Why VahanKhata"
        description="Why transport firms choose VahanKhata over spreadsheets and ERP fleet tools: live fuel checks, WhatsApp intake and fair driver settlement."
        path="/why-us"
      />

      {/* HERO */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-3xl px-4 py-20 text-center sm:py-24 sm:px-6">
          <span className="text-xs font-semibold uppercase tracking-wider text-primary">
            Why VahanKhata
          </span>
          <h1 className="mt-6 text-4xl font-extrabold leading-tight tracking-tight text-foreground sm:text-5xl">
            Spreadsheets lost the money. So did heavy ERPs.
          </h1>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
            ज़्यादा पैसा बचाना है या बिना झगड़े में समझौता होना है — वहीं चाहिए ये सिर्फ़ एक ऐप नहीं, एक सीधा सा ढंग चाहिए।
          </p>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            The WhatsApp your drivers already use, joined to a ledger your owners can trust.
          </p>
        </div>
      </section>

      {/* REASONS */}
      <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
        <div className="grid gap-5 sm:grid-cols-3">
          {REASONS.map((r) => (
            <Card key={r.title} className="p-6 text-center">
              <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <r.icon className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mt-4 text-base font-bold text-foreground">{r.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {r.text}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto mb-24 max-w-3xl px-4 py-16 text-center sm:px-6">
        <h2 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
          See the difference on a live demo.
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base">
          Fifteen minutes, your fleet, your numbers.
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
