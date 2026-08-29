import React from "react";
import Seo from "../Seo";
import { Button } from "../../components/ui/button.jsx";
import { Card } from "../../components/ui/card.jsx";

export default function Cookies() {
  return (
    <>
      <Seo
        title="Cookie Policy"
        description="How VahanKhata uses cookies and similar technologies for authentication, security and analytics."
        path="/cookies"
      />

      {/* HERO */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-3xl px-4 py-20 text-center sm:py-24 sm:px-6">
          <span className="text-xs font-semibold uppercase tracking-wider text-primary">Legal</span>
          <h1 className="mt-6 text-4xl font-extrabold leading-tight tracking-tight text-foreground sm:text-5xl">
            Cookie Policy
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">Last updated: August 2026</p>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground" lang="hi">
            हम कम से कम कुकीज़ इस्तेमाल करते हैं — साइन-इन और सुरक्षा के लिए ज़रूरी कुकीज़ हमेशा लगती हैं, एनालिटिक्स सिर्फ
            आपकी मर्ज़ी से। विज्ञापन या क्रॉस-साइट ट्रैकिंग कुकीज़ नहीं।
          </p>
        </div>
      </section>

      {/* CONTENT */}
      <section className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <Card className="px-6 py-8">
          <div className="prose prose-sm max-w-none">
            <p>
              This Cookie Policy explains how VahanKhata uses cookies and similar technologies when you visit our site or
              use our platform. We keep tracking minimal and only where it provides a genuine benefit.
            </p>
            <h2>1. What are cookies?</h2>
            <p>
              Cookies are small text files stored on your device. They help a site remember your session and preferences.
            </p>
            <h2>2. Cookies we use</h2>
            <ul>
              <li>
                <strong>Essential / authentication:</strong> required to keep you signed in and to protect your account.
                These are always active.
              </li>
              <li>
                <strong>Security:</strong> used to detect or prevent abuse and to enforce rate limits (e.g. contact-form
                cooldowns).
              </li>
              <li>
                <strong>Analytics (optional):</strong> used, only if enabled, to understand aggregate site usage and
                improve our pages. We do not use advertising or cross-site tracking cookies.
              </li>
            </ul>
            <h2>3. Managing cookies</h2>
            <p>
              You can control or delete cookies in your browser settings. Disabling essential cookies may prevent you from
              signing in or using parts of the platform.
            </p>
            <h2>4. Contact</h2>
            <p>
              Questions about cookies? Email <a href="mailto:support@vahankhata.in">support@vahankhata.in</a>.
            </p>
          </div>
        </Card>
      </section>

      {/* CTA */}
      <section className="mx-auto mb-24 max-w-3xl px-4 py-16 text-center sm:px-6">
        <h2 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
          Still got questions?
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base">
          Book a free demo — see the full trip-to-settlement flow without a spreadsheet.
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Button asChild size="lg">
            <a href="/request-demo">Book a demo</a>
          </Button>
          <Button asChild size="lg" variant="outline">
            <a href="/">Log in</a>
          </Button>
        </div>
      </section>
    </>
  );
}
