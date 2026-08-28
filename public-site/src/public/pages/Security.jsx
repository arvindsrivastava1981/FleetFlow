import React from "react";
import Seo from "../Seo";
import { Button } from "../../components/ui/button.jsx";
import { Card } from "../../components/ui/card.jsx";
import { Lock, Clock, FileText, Receipt } from "lucide-react";

const PILLARS = [
  [Lock, "Role-based access", "Super-admin, trip-manager and driver roles each see only what they should. Fleet and asset data is scoped per firm."],
  [Clock, "Time-limited sessions", "Sessions are time-limited, and expired or invalid tokens are rejected, so abandoned logins don't linger."],
  [FileText, "Immutable audit trail", "Every entitlement change, settlement and sensitive action is written to an audit ledger, so nothing quietly disappears."],
  [Receipt, "Tamper-evident settlements", "Every settled trip carries a verification hash, so a settlement record can't be quietly altered after the fact."],
];

export default function Security() {
  return (
    <>
      <Seo
        title="Security"
        description="How VahanKhata protects fleet data: role-based access, time-limited sessions, audit logging and tamper-evident settlements."
        path="/security"
      />

      {/* HERO */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-3xl px-4 py-20 text-center sm:py-24 sm:px-6">
          <span className="text-xs font-semibold uppercase tracking-wider text-primary">
            Security
          </span>
          <h1 className="mt-6 text-4xl font-extrabold leading-tight tracking-tight text-foreground sm:text-5xl">
            Your fleet data, guarded like a fleet.
          </h1>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
            सही इंसान को सही चीज़ दिखे, हर बदलाव दर्ज हो — और ज़रूरत के वक़्त कोई शोर न हो।
          </p>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            Role-based access, audit ledgers and tamper-evident settlements — so nothing goes unseen or unrecorded.
          </p>
        </div>
      </section>

      {/* PILLARS */}
      <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
        <div className="grid gap-5 sm:grid-cols-2">
          {PILLARS.map(([Icon, title, text]) => (
            <Card key={title} className="p-6">
              <Icon className="h-6 w-6 text-primary" />
              <h3 className="mt-3 text-lg font-bold text-foreground">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                {text}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {/* DETAILS */}
      <section className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <div className="prose prose-sm max-w-none text-muted-foreground">
          <h2 className="text-xl font-bold text-foreground">How we protect your data</h2>
          <p>
            VahanKhata applies defence-in-depth across authentication, entitlements and audit. Each firm (fleet) is a
            tenant; users and records are scoped to that firm. Administrative actions are restricted to the relevant role.
          </p>
          <h3 className="text-base font-bold text-foreground">Authentication &amp; sessions</h3>
          <ul>
            <li>One-time passcodes (OTPs) for identity verification with expiry and attempt limits.</li>
            <li>Time-limited sessions that require re-authentication when they lapse.</li>
            <li>Role-based guards enforce what each user may view or change.</li>
          </ul>
          <h3 className="text-base font-bold text-foreground">Data integrity &amp; audit</h3>
          <ul>
            <li>Dedicated audit ledgers for billing/entitlement changes.</li>
            <li>Settlement records carry verification hashes for tamper-evidence.</li>
            <li>Login lockout after repeated failed sign-in attempts.</li>
          </ul>
          <p>
            No platform can guarantee absolute security. We continuously review our controls and follow responsible
            disclosure for any finding. Report concerns to{" "}
            <a href="mailto:security@vahankhata.in" className="font-medium text-primary">
              security@vahankhata.in
            </a>.
          </p>
        </div>
      </section>

      {/* CLOSING CTA */}
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