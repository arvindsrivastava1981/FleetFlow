import React from "react";
import Seo from "../Seo";
import { Button } from "../../components/ui/button.jsx";
import { Card } from "../../components/ui/card.jsx";

export default function Terms() {
  return (
    <>
      <Seo
        title="Terms of Service"
        description="The terms and conditions governing your use of VahanKhata.in's fleet expense and trip management platform."
        path="/terms"
      />

      {/* HERO */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-3xl px-4 py-20 text-center sm:py-24 sm:px-6">
          <span className="text-xs font-semibold uppercase tracking-wider text-primary">Legal</span>
          <h1 className="mt-6 text-4xl font-extrabold leading-tight tracking-tight text-foreground sm:text-5xl">
            Terms of Service
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">Last updated: August 2026</p>
          <p className="mt-3 text-sm leading-relaxed text-muted-foreground" lang="hi">
            ये शर्तें बताती हैं कि VahanKhata.in सेवा का इस्तेमाल कैसे करें — अकाउंट की ज़िम्मेदारी, Razorpay से बिलिंग, डेटा का
            मालिकाना हक़ और सेवा रोकने/बंद करने के नियम। पूरी शर्तें नीचे अंग्रेज़ी में हैं।
          </p>
        </div>
      </section>

      {/* CONTENT */}
      <section className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <Card className="px-6 py-8">
          <div className="prose prose-sm max-w-none">
            <p>
              These Terms of Service ("Terms") govern your access to and use of VahanKhata.in ("the Service"). By creating an
              account or using the Service you agree to these Terms.
            </p>
            <h2>1. Your account</h2>
            <p>
              You are responsible for the accuracy of the information you provide and for safeguarding your credentials. You
              must not share accounts or allow unauthorised access. Notify us immediately of any suspected misuse.
            </p>
            <h2>2. Use of the Service</h2>
            <p>
              You may use the Service only for lawful purposes and in accordance with these Terms. You agree not to misuse,
              reverse-engineer, or attempt to disrupt the Service, or to use it to violate any law or the rights of others,
              including drivers within your fleet.
            </p>
            <h2>3. Subscriptions &amp; billing</h2>
            <p>
              Paid plans are billed via Razorpay on the cycle you select. Trial, Monthly and Yearly plans have the features
              described on the Pricing page. You may add extra vehicle slots; these are billed according to the rates shown
              at purchase. Fees are generally non-refundable except where required by law.
            </p>
            <h2>4. Intellectual property</h2>
            <p>
              The Service, its software and content are owned by VahanKhata.in and its licensors. Unless permitted by law, you
              may not copy, modify, distribute or create derivative works without our written consent.
            </p>
            <h2>5. Data you provide</h2>
            <p>
              You retain ownership of the data you enter. You grant us a licence to host, process and present it to provide
              the Service, as detailed in our Privacy Policy. You are responsible for ensuring you have the right to
              submit third-party data (for example, driver information).
            </p>
            <h2>6. Limitation of liability</h2>
            <p>
              The Service is provided "as is". To the maximum extent permitted by law, VahanKhata.in is not liable for indirect,
              incidental or consequential damages. Your use of the Service is at your own risk.
            </p>
            <h2>7. Suspension &amp; termination</h2>
            <p>
              We may suspend or terminate access for breach of these Terms, non-payment, or conduct that risks the Service
              or others. You may stop using the Service and close your account at any time.
            </p>
            <h2>8. Changes</h2>
            <p>
              We may update these Terms from time to time. Material changes will be communicated to you. Continued use of
              the Service after changes constitutes acceptance.
            </p>
            <h2>9. Contact</h2>
            <p>
              For questions about these Terms, contact us at <a href="mailto:support@vahankhata.in">support@vahankhata.in</a>.
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
