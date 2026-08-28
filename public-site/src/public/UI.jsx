import * as React from "react";
import { app } from "../config.js";
import { Button } from "../components/ui/button.jsx";

/** Section heading: eyebrow + title + lead. */
export function SectionHead({ eyebrow, title, lead, align = "center" }) {
  const alignCls =
    align === "left" ? "items-start text-left" : "items-center text-center";
  return (
    <div className={`mx-auto flex max-w-2xl flex-col ${alignCls}`}>
      {eyebrow && <span className="market-eyebrow">{eyebrow}</span>}
      <h2 className="market-title">{title}</h2>
      {lead && <p className="market-lead">{lead}</p>}
    </div>
  );
}

/** Single-accent icon chip (indigo). */
export function IconChip({ children, tone = "brand", className = "" }) {
  return (
    <div
      className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary ${className}`}
    >
      {children}
    </div>
  );
}

/** Light, minimal top band shared by all non-home public pages. */
export function PageHero({ eyebrow, title, lead, children }) {
  return (
    <section className="border-b border-border bg-background">
      <div className="market-wrap py-16 text-center sm:py-20">
        {eyebrow && <span className="market-eyebrow">{eyebrow}</span>}
        <h1 className="mx-auto mt-4 max-w-3xl text-balance text-4xl font-extrabold leading-[1.08] tracking-tight text-foreground sm:text-5xl">
          {title}
        </h1>
        {lead && (
          <p className="mx-auto mt-4 max-w-2xl text-pretty text-base leading-relaxed text-muted-foreground sm:text-lg">
            {lead}
          </p>
        )}
        {children && <div className="mt-8">{children}</div>}
      </div>
    </section>
  );
}

/** English headline with an optional Hindi line beneath. */
export function BiHead({ en, hi, hiClass = "text-muted-foreground" }) {
  return (
    <span className="block">
      {en}
      {hi && (
        <span className={`mt-1 block font-medium ${hiClass}`}>{hi}</span>
      )}
    </span>
  );
}

/** Short Hindi summary box at the top of English legal pages. */
export function HiNote({ children }) {
  return (
    <div className="market-wrap">
      <div className="mx-auto mt-6 max-w-3xl rounded-xl border border-brand-100 bg-brand-50/60 p-4 text-[15px] leading-relaxed text-ink-700">
        <span className="font-bold text-brand-700">हिंदी में सारांश: </span>
        {children}
      </div>
    </div>
  );
}

/** Simple prose wrapper for legal/long-form pages. */
export function Prose({ children }) {
  return (
    <div className="market-section market-wrap">
      <div className="mx-auto max-w-3xl space-y-5 text-[15px] leading-relaxed text-muted-foreground [&>h2]:mt-8 [&>h2]:text-xl [&>h2]:font-bold [&>h2]:text-foreground [&>h3]:mt-6 [&>h3]:text-base [&>h3]:font-bold [&>h3]:text-foreground [&>ul]:list-disc [&>ul]:space-y-1.5 [&>ul]:pl-5 [&>p>strong]:font-semibold">
        {children}
      </div>
    </div>
  );
}

/** Minimal closing CTA band. */
export function CTABand({
  title = "Ready to take control of your fleet?",
  lead = "Book a free demo — see the full trip-to-settlement flow without a spreadsheet.",
  ctaText = "Book a demo",
  ctaHref = "/request-demo",
  ghostText = "Log in",
  ghostHref = app("/"),
}) {
  return (
    <section className="market-section market-wrap">
      <div className="mx-auto flex max-w-3xl flex-col items-center rounded-2xl border border-border bg-primary/5 px-6 py-14 text-center">
        <h2 className="text-balance text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
          {title}
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-pretty text-sm leading-relaxed text-muted-foreground sm:text-base">
          {lead}
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Button asChild size="lg">
            <a href={ctaHref}>{ctaText}</a>
          </Button>
          <Button asChild size="lg" variant="outline">
            <a href={ghostHref}>{ghostText}</a>
          </Button>
        </div>
      </div>
    </section>
  );
}