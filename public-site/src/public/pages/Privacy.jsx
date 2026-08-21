import React from "react";
import Seo from "../Seo";
import { PageHero, Prose } from "../UI";

export default function Privacy() {
  return (
    <>
      <Seo
        title="Privacy Policy"
        description="How VahanKhata collects, uses and protects your data, including phone numbers, OTPs, and fleet operational data."
        path="/privacy"
      />
      <PageHero eyebrow="Legal" title="Privacy Policy" lead="Last updated: August 2026" />
      <Prose>
        <p>
          This Privacy Policy explains how VahanKhata ("we", "our") collects, uses and protects your information when
          you use our fleet expense &amp; trip management platform (the "Service"). By using the Service you agree to
          the practices described below.
        </p>
        <h2>1. Information we collect</h2>
        <p>
          We collect the information you provide directly: account details (name, phone number, email, firm), driver
          and vehicle details, trip and expense records, and any photos or WhatsApp messages you submit. We also
          collect limited technical data (e.g. IP address) to keep the Service secure.
        </p>
        <h2>2. How we use your information</h2>
        <ul>
          <li>To operate and improve the Service (trip, expense, Driver Salery and settlement tracking).</li>
          <li>To authenticate you, including one-time passcodes (OTPs).</li>
          <li>To communicate operational updates, billing and support messages.</li>
          <li>To maintain audit logs and comply with legal obligations.</li>
        </ul>
        <h2>3. Driver consent</h2>
        <p>
          Where employers submit driver data or employees interact with the Service (e.g. via WhatsApp or a QR tag),
          we rely on the submitting organisation to ensure it has appropriate consent. Where applicable, drivers are
          given the ability to consent to trips in-app.
        </p>
        <h2>4. Data sharing</h2>
        <p>
          We do not sell your personal data. We share data only with sub-processors we engage to run the Service (e.g.
          payment processing via Razorpay, messaging/WhatsApp integration and hosting) under obligations of
          confidentiality.
        </p>
        <h2>5. Data retention &amp; security</h2>
        <p>
          We retain data only as long as needed for the purposes above or as required by law. We apply role-based
          access, time-limited sessions and audit logging. No system is 100% secure; we work to protect your data and
          will notify you of any material breach as required.
        </p>
        <h2>6. Your rights</h2>
        <p>
          You may request access to, correction of, or deletion of your personal data, subject to legal retention
          requirements. Contact us via the details below.
        </p>
        <h2>7. Contact</h2>
        <p>
          For privacy questions, contact us at <a href="mailto:hello@vahankhata.in">hello@vahankhata.in</a>.
        </p>
      </Prose>
    </>
  );
}