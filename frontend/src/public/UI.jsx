import React from "react";

/** Section wrapper: eyebrow + title + lead, centred. */
export function SectionHead({ eyebrow, title, lead, align = "center" }) {
  const alignCls = align === "left" ? "items-start text-left" : "items-center text-center";
  return (
    <div className={`flex ${alignCls} flex-col`}>
      {eyebrow && <span className="market-eyebrow">{eyebrow}</span>}
      <h2 className="market-title">{title}</h2>
      {lead && <p className="market-lead">{lead}</p>}
    </div>
  );
}

/** Icon chip used across feature/stat grids. */
export function IconChip({ children, tone = "brand" }) {
  const tones = {
    brand: "bg-brand-100 text-brand-700",
    emerald: "bg-emerald-100 text-emerald-700",
    amber: "bg-amber-100 text-amber-700",
    sky: "bg-sky-100 text-sky-700",
    rose: "bg-rose-100 text-rose-700",
    violet: "bg-violet-100 text-violet-700",
    slate: "bg-ink-100 text-ink-700",
  };
  return (
    <div
      className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl text-xl ${
        tones[tone] || tones.brand
      }`}
    >
      {children}
    </div>
  );
}

/** Top hero band shared by all non-home public pages. */
export function PageHero({ eyebrow, title, lead, children }) {
  return (
    <section className="market-band relative overflow-hidden">
      <div className="market-grid absolute inset-0 opacity-60" aria-hidden />
      <div className="market-wrap relative py-16 text-center sm:py-20">
        {eyebrow && <span className="market-eyebrow !border-white/25 !bg-white/10 !text-brand-100">{eyebrow}</span>}
        <h1 className="mt-5 text-balance text-3xl font-extrabold leading-[1.1] tracking-tight text-white sm:text-4xl lg:text-5xl">
          {title}
        </h1>
        {lead && (
          <p className="mx-auto mt-4 max-w-2xl text-pretty text-base leading-relaxed text-brand-100 sm:text-lg">
            {lead}
          </p>
        )}
        {children}
      </div>
    </section>
  );
}

/** Simple prose wrapper for legal/long-form pages. */
export function Prose({ children }) {
  return (
    <div className="market-section market-wrap">
      <div className="mx-auto max-w-3xl space-y-5 text-[15px] leading-relaxed text-ink-700 [&>h2]:mt-8 [&>h2]:text-xl [&>h2]:font-bold [&>h2]:text-ink-900 [&>h3]:mt-6 [&>h3]:text-base [&>h3]:font-bold [&>h3]:text-ink-900 [&>ul]:list-disc [&>ul]:space-y-1.5 [&>ul]:pl-5 [&>p>strong]:font-semibold">
        {children}
      </div>
    </div>
  );
}
export function CTABand({
  title = "Ready to take control of your fleet?",
  lead = "See how FleetFlow replaces spreadsheets and WhatsApp hassle with one clean workflow — from trip start to batta settlement.",
  ctaText = "Book a demo",
  ctaHref = "/request-demo",
  ghostText = "Log in",
  ghostHref = "/login",
}) {
  return (
    <section className="market-wrap pb-16 sm:pb-24">
      <div className="market-band relative overflow-hidden rounded-3xl px-6 py-12 text-center shadow-xl sm:px-12 sm:py-16">
        <div className="market-grid absolute inset-0 opacity-60" aria-hidden />
        <div className="relative">
          <h2 className="text-balance text-2xl font-extrabold tracking-tight text-white sm:text-3xl lg:text-4xl">
            {title}
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-pretty text-sm leading-relaxed text-brand-100 sm:text-base">
            {lead}
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <a href={ctaHref} className="market-btn market-btn-brand !bg-white !text-brand-900 hover:!bg-brand-50">
              {ctaText}
            </a>
            <a href={ghostHref} className="market-btn market-btn-dark">
              {ghostText}
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}