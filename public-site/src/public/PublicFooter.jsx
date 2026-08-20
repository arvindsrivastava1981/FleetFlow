import { app } from "../config.js";

const FOOTER_COLUMNS = [
  {
    title: "Product",
    links: [
      { label: "Features", to: "/features" },
      { label: "Why FleetFlow", to: "/why-us" },
      { label: "Pricing", to: "/pricing" },
      { label: "About", to: "/about" },
      { label: "Book a demo", to: "/request-demo" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", to: "/about" },
      { label: "Contact", to: "/contact" },
      { label: "Log in", to: app("/") },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy Policy", to: "/privacy" },
      { label: "Terms of Service", to: "/terms" },
      { label: "Security", to: "/security" },
    ],
  },
];

function FooterCol({ title, links }) {
  return (
    <div>
      <h4 className="text-sm font-bold text-white">{title}</h4>
      <ul className="mt-4 space-y-2.5">
        {links.map((l) => (
          <li key={l.label}>
            <a href={l.to} className="text-sm text-brand-100/80 transition hover:text-white">
              {l.label}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function PublicFooter() {
  return (
    <footer className="market-band">
      <div className="market-wrap py-14">
        <div className="grid gap-10 md:grid-cols-4">
          <div>
            <a href="/" className="flex items-center gap-2">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/15 text-base font-black text-white">
                F
              </span>
              <span className="text-lg font-extrabold tracking-tight text-white">
                Fleet<span className="text-brand-200">Flow</span>
              </span>
            </a>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-brand-100/80">
              The all-in-one fleet expense &amp; trip management platform built for Indian transport firms — from trip
              start to batta settlement.
            </p>
          </div>

          {FOOTER_COLUMNS.map((c) => (
            <FooterCol key={c.title} title={c.title} links={c.links} />
          ))}
        </div>

        <div className="mt-12 flex flex-col items-start justify-between gap-3 border-t border-white/15 pt-6 text-xs text-brand-100/70 sm:flex-row sm:items-center">
          <span>© {new Date().getFullYear()} FleetFlow Technologies. All rights reserved.</span>
          <span>Made for Indian fleet &amp; transport operations.</span>
        </div>
      </div>
    </footer>
  );
}