import { useEffect } from "react";

/**
 * Lightweight per-page head setter for the public marketing site.
 * Sets <title>, meta description, canonical and Open Graph tags so each
 * marketing page is crawlable with its own unique keywords/snippet.
 * No external dependency — plain DOM writes on mount.
 */
export default function Seo({ title, description, path }) {
  useEffect(() => {
    const base = "FleetFlow — Smart Fleet Expense & Trip Management";
    document.title = title ? `${title} | FleetFlow` : base;

    const set = (attr, key, val) => {
      let el = document.head.querySelector(`meta[${attr}="${key}"]`);
      if (!el) {
        el = document.createElement("meta");
        el.setAttribute(attr, key);
        document.head.appendChild(el);
      }
      el.setAttribute("content", val);
    };

    set("name", "description", description ?? "");
    set("property", "og:title", title ? `${title} | FleetFlow` : base);
    set("property", "og:description", description ?? "");
    set("property", "og:type", "website");
    if (path) set("property", "og:url", path);

    const linkSel = document.head.querySelector('link[rel="canonical"]');
    if (path) {
      if (linkSel) linkSel.setAttribute("href", path);
      else {
        const l = document.createElement("link");
        l.setAttribute("rel", "canonical");
        l.setAttribute("href", path);
        document.head.appendChild(l);
      }
    }
  }, [title, description, path]);

  return null;
}