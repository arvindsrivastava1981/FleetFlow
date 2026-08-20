import { Routes, Route } from "react-router-dom";
import PublicLayout from "./public/PublicLayout.jsx";
import HomePage from "./public/pages/Home.jsx";
import AboutPage from "./public/pages/About.jsx";
import WhyUsPage from "./public/pages/WhyUs.jsx";
import FeaturesPage from "./public/pages/Features.jsx";
import PricingPage from "./public/pages/Pricing.jsx";
import FaqPage from "./public/pages/Faq.jsx";
import ContactPage from "./public/pages/Contact.jsx";
import PrivacyPage from "./public/pages/Privacy.jsx";
import TermsPage from "./public/pages/Terms.jsx";
import SecurityPage from "./public/pages/Security.jsx";
import CookiesPage from "./public/pages/Cookies.jsx";

function NotFound() {
  return (
    <div className="market-section market-wrap text-center">
      <p className="text-6xl font-black text-brand-600">404</p>
      <h1 className="mt-4 text-2xl font-bold text-ink-900">Page not found</h1>
      <p className="mt-2 text-sm text-ink-500">
        The page you're looking for doesn't exist or has moved.
      </p>
      <a href="/" className="market-btn market-btn-brand mt-8">
        Back to home
      </a>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<PublicLayout><HomePage /></PublicLayout>} />
      <Route path="/about" element={<PublicLayout><AboutPage /></PublicLayout>} />
      <Route path="/why-us" element={<PublicLayout><WhyUsPage /></PublicLayout>} />
      <Route path="/features" element={<PublicLayout><FeaturesPage /></PublicLayout>} />
      <Route path="/pricing" element={<PublicLayout><PricingPage /></PublicLayout>} />
      <Route path="/faq" element={<PublicLayout><FaqPage /></PublicLayout>} />
      <Route path="/contact" element={<PublicLayout><ContactPage /></PublicLayout>} />
      <Route path="/request-demo" element={<PublicLayout><ContactPage /></PublicLayout>} />
      <Route path="/privacy" element={<PublicLayout><PrivacyPage /></PublicLayout>} />
      <Route path="/terms" element={<PublicLayout><TermsPage /></PublicLayout>} />
      <Route path="/security" element={<PublicLayout><SecurityPage /></PublicLayout>} />
      <Route path="/cookies" element={<PublicLayout><CookiesPage /></PublicLayout>} />
      <Route path="*" element={<PublicLayout><NotFound /></PublicLayout>} />
    </Routes>
  );
}