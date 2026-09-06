import { app } from "../config.js";
import Logo from "./Logo.jsx";

const FOOTER_COLUMNS = [
  {
    title: "Product",
    links: [
      { label: "Features", to: "/features" },
      { label: "Pricing", to: "/pricing" },
      { label: "FAQ", to: "/faq" },
      { label: "Start free trial", to: "/request-demo" },
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
      { label: "Privacy", to: "/privacy" },
      { label: "Terms", to: "/terms" },
      { label: "Security", to: "/security" },
      { label: "Cookies", to: "/cookies" },
    ],
  },
];

function FooterCol({ title, links }) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-foreground">{title}</h4>
      <ul className="mt-4 space-y-2.5">
        {links.map((l) => (
          <li key={l.label}>
            <a
              href={l.to}
              className="text-sm text-muted-foreground transition hover:text-foreground"
            >
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
    <footer className="border-t border-border bg-muted/40">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid gap-10 md:grid-cols-4">
          <div>
            <a href="/" className="flex items-center gap-2" aria-label="VahanKhata.in — home">
              <Logo />
            </a>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-muted-foreground">
              Fleet expense verification, fuel checks and fair driver settlement — from trip start to sign-off.
            </p>
          </div>

          {FOOTER_COLUMNS.map((c) => (
            <FooterCol key={c.title} title={c.title} links={c.links} />
          ))}
        </div>

        <div className="mt-12 flex flex-col items-start justify-between gap-3 border-t border-border pt-6 text-xs text-muted-foreground sm:flex-row sm:items-center">
          <span>© {new Date().getFullYear()} VahanKhata.in. All rights reserved.</span>
          <span>Made for Indian fleet &amp; transport operations.</span>
        </div>
      </div>
    </footer>
  );
}