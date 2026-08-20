import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import PublicNav from "./PublicNav";
import PublicFooter from "./PublicFooter";

/**
 * Shell for all public marketing pages. No auth guard here — unlike the
 * authenticated <Layout>. Add per-page SEO via the <Seo> component inside
 * each child page.
 *
 * NOTE: scroll is reset to the top on every route change here with a plain
 * useLocation() effect instead of <ScrollRestoration />, because
 * <ScrollRestoration /> requires a data router (RouterProvider +
 * createBrowserRouter). This site uses the declarative <BrowserRouter>,
 * where <ScrollRestoration /> throws "must be used within a data router"
 * and blanks the page.
 */
export default function PublicLayout({ children }) {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  return (
    <div className="min-h-screen bg-ink-50 text-ink-900">
      <PublicNav />
      <main>{children}</main>
      <PublicFooter />
    </div>
  );
}