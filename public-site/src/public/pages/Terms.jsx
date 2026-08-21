import React from "react";
import Seo from "../Seo";
import { PageHero, Prose } from "../UI";

export default function Terms() {
  return (
    <>
      <Seo
        title="Terms of Service"
        description="The terms and conditions governing your use of VahanKhata's fleet expense and trip management platform."
        path="/terms"
      />
      <PageHero eyebrow="Legal" title="Terms of Service" lead="Last updated: August 2026" />
      <Prose>
        <p>
          These Terms of Service ("Terms") govern your access to and use of VahanKhata ("the Service"). By creating an
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
          The Service, its software and content are owned by VahanKhata and its licensors. Unless permitted by law, you
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
          The Service is provided "as is". To the maximum extent permitted by law, VahanKhata is not liable for indirect,
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
          For questions about these Terms, contact us at <a href="mailto:hello@vahankhata.in">hello@vahankhata.in</a>.
        </p>
      </Prose>
    </>
  );
}