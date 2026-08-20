import React from "react";
import { ScrollRestoration } from "react-router-dom";
import PublicNav from "./PublicNav";
import PublicFooter from "./PublicFooter";

/**
 * Shell for all public marketing pages. No auth guard here — unlike the
 * authenticated <Layout>. Add per-page SEO via the <Seo> component inside
 * each child page.
 */
export default function PublicLayout({ children }) {
  return (
    <div className="min-h-screen bg-ink-50 text-ink-900">
      <ScrollRestoration />
      <PublicNav />
      <main>{children}</main>
      <PublicFooter />
    </div>
  );
}