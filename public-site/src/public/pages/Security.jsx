import React from "react";
import Seo from "../Seo";
import { PageHero, Prose, HiNote } from "../UI";

const PILLARS = [
  ["🔐", "Role-based access", "Super-admin, trip-manager and driver roles each see only what they should. Fleet and asset data is scoped per firm."],
  ["⏱️", "Time-limited sessions", "Sessions are time-limited, and expired or invalid tokens are rejected, so abandoned logins don't linger."],
  ["📜", "Immutable audit trail", "Every entitlement change, settlement and sensitive action is written to an audit ledger, so nothing quietly disappears."],
  ["🧾", "Tamper-evident settlements", "Every settled trip carries a verification hash, so a settlement record can't be quietly altered after the fact."],
];

export default function Security() {
  return (
    <>
      <Seo
        title="Security"
        description="How VahanKhata protects fleet data: role-based access, time-limited sessions, audit logging and tamper-evident settlements."
        path="/security"
      />
      <PageHero
        eyebrow="Security"
        title="Your fleet data, guarded like a fleet."
        lead="सही इंसान को सही चीज़ दिखे, हर बदलाव दर्ज हो — और ज़रूरत के वक़्त कोई शोर न हो।"
      />
      <HiNote>
        आपका फ्लीट डेटा रोल के हिसाब से गेट है — सुपर-एडमिन, ट्रिप-मैनेजर और ड्राइवर सिर्फ अपना हिस्सा देखते हैं। सेशन
        समय-सीमित हैं, हर बदलाव का ऑडिट लेजर है, और हर सेटल्ड ट्रिप पर वेरिफिकेशन हैश होता है। कोई सुरक्षा समस्या हो तो:
        security@vahankhata.in
      </HiNote>
      <section className="market-section market-wrap">
        <div className="grid gap-5 sm:grid-cols-2">
          {PILLARS.map(([icon, title, text]) => (
            <div key={title} className="rounded-xl border border-border bg-card p-6">
              <span className="text-2xl">{icon}</span>
              <h3 className="mt-3 text-lg font-bold text-ink-900">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-600">{text}</p>
            </div>
          ))}
        </div>
      </section>
      <Prose>
        <h2>How we protect your data</h2>
        <p>
          VahanKhata applies defence-in-depth across authentication, entitlements and audit. Each firm (fleet) is a
          tenant; users and records are scoped to that firm. Administrative actions are restricted to the relevant role.
        </p>
        <h3>Authentication &amp; sessions</h3>
        <ul>
          <li>One-time passcodes (OTPs) for identity verification with expiry and attempt limits.</li>
          <li>Time-limited sessions that require re-authentication when they lapse.</li>
          <li>Role-based guards enforce what each user may view or change.</li>
        </ul>
        <h3>Data integrity &amp; audit</h3>
        <ul>
          <li>Dedicated audit ledgers for billing/entitlement changes.</li>
          <li>Settlement records carry verification hashes for tamper-evidence.</li>
          <li>Login lockout after repeated failed sign-in attempts.</li>
        </ul>
        <p>
          No platform can guarantee absolute security. We continuously review our controls and follow responsible
          disclosure for any finding. Report concerns to{" "}
          <a href="mailto:security@vahankhata.in">security@vahankhata.in</a>.
        </p>
      </Prose>
    </>
  );
}