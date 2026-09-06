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
        description="VahanKhata.in verifies fuel, tracks trips and settles driver salary for Indian transport firms. Trip start to settlement on WhatsApp."
        path="/"
      />

      {/* HERO + WHATSAPP MOCKUP */}
      <section className="border-b border-border bg-gradient-to-b from-primary/5 to-transparent">
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 py-20 sm:px-6 lg:grid-cols-2 lg:py-28">
          <div className="text-center lg:text-left">
            <span className="text-xs font-semibold uppercase tracking-wider text-primary">
              Fleet expense &amp; trip management
            </span>
            <h1 className="mt-5 text-4xl font-extrabold leading-tight tracking-tight text-foreground sm:text-5xl">
              Every rupee your fleet spends, accounted for.
            </h1>
            <p className="mt-5 text-base leading-relaxed text-muted-foreground sm:text-lg" lang="hi">
              ड्राइवर रसीद WhatsApp पर भेजता है — पेट्रोल, खर्च और वेतन सब अपने आप जाँच होता है।
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row lg:justify-start">
              <Button asChild size="lg">
                <a href="/request-demo">Start free trial</a>
              </Button>
              <a href="/features" className="text-sm font-medium text-muted-foreground underline-offset-4 transition-all duration-200 hover:text-foreground hover:underline">
                See how it works →
              </a>
            </div>
            <p className="mt-4 text-xs text-muted-foreground">
              Free 15-day trial · No credit card
            </p>
          </div>

          {/* Pure-Tailwind WhatsApp chat mockup — zero image bytes */}
          <div className="mx-auto w-full max-w-sm rounded-2xl border border-border bg-card shadow-md" aria-label="WhatsApp receipt example">
            <div className="flex items-center gap-2 rounded-t-2xl border-b border-border bg-[#075E54] px-4 py-3 text-white">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-white/20 text-xs font-bold">VK</span>
              <div className="text-sm font-medium">VahanKhata.in</div>
            </div>
            <div className="space-y-3 px-4 py-5 text-sm">
              <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-muted px-4 py-2.5 text-muted-foreground">
                Driver · HP12 AB 3456<br />Petrol ₹2,400 — IOC Solapur
              </div>
              <div className="ml-auto max-w-[85%] rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-primary-foreground">
                ✓ Receipt verified · Rate ok
              </div>
              <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-muted px-4 py-2.5 text-muted-foreground">
                Trip settled — PDF signed
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* STATS */}
      <section className="border-b border-border">
        <div className="mx-auto grid max-w-4xl grid-cols-3 gap-4 px-4 py-10 text-center sm:px-6">
          {[["₹10L+", "fuel verified"], ["500+", "trips settled"], ["0", "apps for drivers"]].map(([v, l]) => (
            <div key={l}>
              <p className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">{v}</p>
              <p className="mt-1 text-xs text-muted-foreground sm:text-sm">{l}</p>
            </div>
          ))}
        </div>
      </section>

      {/* THREE PILLARS */}
      <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:py-20">
        <div className="grid gap-5 sm:grid-cols-3">
          {PILLARS.map((p) => (
            <Card key={p.title} className="p-6 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
                <p.icon className="h-5 w-5" />
              </div>
              <h2 className="mt-4 text-base font-bold text-foreground">{p.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{p.text}</p>
            </Card>
          ))}
        </div>
        <div className="mt-12 text-center">
          <Button asChild size="lg">
            <a href="/request-demo">Book a free demo</a>
          </Button>
        </div>
      </section>
    </>
  );
}