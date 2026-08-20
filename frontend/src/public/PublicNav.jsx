import { useState } from "react";

const LINKS = [
  { to: "/", label: "Home" },
  { to: "/features", label: "Features" },
  { to: "/why-us", label: "Why Us" },
  { to: "/pricing", label: "Pricing" },
  { to: "/about", label: "About" },
  { to: "/contact", label: "Contact" },
];

export default function PublicNav() {
  const [open, setOpen] = useState(false);
  return (
    <header className="sticky top-0 z-50 border-b border-ink-200/70 bg-white/85 backdrop-blur">
      <div className="market-wrap flex h-16 items-center justify-between gap-4">
        <a href="/" className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-base font-black text-white">
            F
          </span>
          <span className="text-lg font-extrabold tracking-tight text-ink-900">
            Fleet<span className="text-brand-600">Flow</span>
          </span>
        </a>

        <nav className="hidden items-center gap-1 lg:flex">
          {LINKS.map((l) => (
            <a
              key={l.to}
              href={l.to}
              className="rounded-lg px-3 py-2 text-sm font-medium text-ink-600 transition hover:bg-ink-100 hover:text-ink-900"
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="hidden items-center gap-2 lg:flex">
          <a href="/login" className="market-btn market-btn-ghost !px-4 !py-2">
            Log in
          </a>
          <a href="/request-demo" className="market-btn market-btn-brand !px-4 !py-2">
            Get a demo
          </a>
        </div>

        <button
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-ink-200 text-ink-700 lg:hidden"
          onClick={() => setOpen((v) => !v)}
          aria-label="Toggle menu"
        >
          {open ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          )}
        </button>
      </div>

      {open && (
        <div className="border-t border-ink-200 bg-white px-5 py-4 lg:hidden">
          <nav className="flex flex-col gap-1">
            {LINKS.map((l) => (
              <a
                key={l.to}
                href={l.to}
                onClick={() => setOpen(false)}
                className="rounded-lg px-3 py-2.5 text-sm font-medium text-ink-700 transition hover:bg-ink-100"
              >
                {l.label}
              </a>
            ))}
            <div className="mt-3 flex flex-col gap-2 border-t border-ink-100 pt-3">
              <a href="/login" className="market-btn market-btn-ghost w-full">
                Log in
              </a>
              <a href="/request-demo" className="market-btn market-btn-brand w-full">
                Get a demo
              </a>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}