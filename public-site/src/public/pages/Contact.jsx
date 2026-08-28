import React, { useState } from "react";
import Seo from "../Seo";
import { Button } from "../../components/ui/button.jsx";
import { Card } from "../../components/ui/card.jsx";
import { Mail, MessageCircle, UserRound } from "lucide-react";
import { app } from "../../config.js";

const CONTACT_EMAIL = "support@vahankhata.in";

export default function Contact() {
  const [form, setForm] = useState({ name: "", firm: "", email: "", phone: "", message: "" });
  const [sent, setSent] = useState(false);
  const update = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const buildMailto = () => {
    const subject = encodeURIComponent(`Contact via site — ${form.firm || form.name || "Inquiry"}`);
    const body = encodeURIComponent(
      `Name: ${form.name}\nFirm: ${form.firm}\nEmail: ${form.email}\nPhone: ${form.phone}\n\n${form.message}`
    );
    return `mailto:${CONTACT_EMAIL}?subject=${subject}&body=${body}`;
  };
  const whatsappLink = `https://wa.me/918860666659?text=${encodeURIComponent(
    `Hi VahanKhata, I'd like a demo. (${form.name || "Inquiry"})`
  )}`;

  const inputCls =
    "w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1";
  const labelCls = "mb-1.5 block text-xs font-semibold text-foreground";

  return (
    <>
      <Seo
        title="Contact Us"
        description="Talk to the VahanKhata team about a demo, pricing or onboarding. Reach us by email or WhatsApp."
        path="/contact"
      />

      {/* HERO */}
      <section className="border-b border-border">
        <div className="mx-auto max-w-3xl px-4 py-20 text-center sm:py-24 sm:px-6">
          <span className="text-xs font-semibold uppercase tracking-wider text-primary">
            Contact
          </span>
          <h1 className="mt-6 text-4xl font-extrabold leading-tight tracking-tight text-foreground sm:text-5xl">
            Let's talk about your fleet.
          </h1>
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
            बस एक संदेश — हम आपका फ्लीट समझेंगे और जल्द से जल्द मदद करेंगे।
          </p>
          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            Book a demo, ask about pricing, or get help onboarding. We reply within one business day.
          </p>
        </div>
      </section>

      {/* CONTACT */}
      <section className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
        <div className="grid gap-8 lg:grid-cols-2">
          {/* Form */}
          <Card className="p-6">
            {sent ? (
              <div className="rounded-xl bg-emerald-50 p-6 text-center">
                <p className="text-lg font-bold text-emerald-700">Almost there!</p>
                <p className="mt-2 text-sm text-emerald-800">
                  Your email app should open with our message pre-filled. Hit send and we'll be in touch.
                </p>
                <Button variant="outline" className="mt-4" onClick={() => setSent(false)}>
                  Write another
                </Button>
              </div>
            ) : (
              <form
                className="space-y-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  window.location.href = buildMailto();
                  setSent(true);
                }}
              >
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className={labelCls}>Name *</label>
                    <input
                      className={inputCls}
                      required
                      value={form.name}
                      onChange={update("name")}
                      placeholder="Rajesh Kumar"
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Company / fleet</label>
                    <input
                      className={inputCls}
                      value={form.firm}
                      onChange={update("firm")}
                      placeholder="Your firm"
                    />
                  </div>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className={labelCls}>Email *</label>
                    <input
                      className={inputCls}
                      required
                      type="email"
                      value={form.email}
                      onChange={update("email")}
                      placeholder="you@firm.com"
                    />
                  </div>
                  <div>
                    <label className={labelCls}>Phone</label>
                    <input
                      className={inputCls}
                      value={form.phone}
                      onChange={update("phone")}
                      placeholder="+91 …"
                    />
                  </div>
                </div>
                <div>
                  <label className={labelCls}>Message *</label>
                  <textarea
                    className={`${inputCls} min-h-28`}
                    required
                    value={form.message}
                    onChange={update("message")}
                    placeholder="How many vehicles and drivers do you run?"
                  />
                </div>
                <Button type="submit" className="w-full">
                  Send message
                </Button>
              </form>
            )}
          </Card>

          {/* Details */}
          <div className="space-y-4">
            <Card className="p-6">
              <div className="flex items-center gap-2">
                <Mail className="h-5 w-5 text-primary" />
                <h3 className="text-base font-bold text-foreground">Email</h3>
              </div>
              <p className="mt-2">
                <a href={`mailto:${CONTACT_EMAIL}`} className="font-medium text-primary">
                  {CONTACT_EMAIL}
                </a>
              </p>
            </Card>
            <Card className="p-6">
              <div className="flex items-center gap-2">
                <MessageCircle className="h-5 w-5 text-primary" />
                <h3 className="text-base font-bold text-foreground">WhatsApp</h3>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">The fastest way to reach us.</p>
              <Button asChild className="mt-4">
                <a href={whatsappLink}>Message on WhatsApp</a>
              </Button>
            </Card>
            <Card className="p-6">
              <div className="flex items-center gap-2">
                <UserRound className="h-5 w-5 text-primary" />
                <h3 className="text-base font-bold text-foreground">Already a customer?</h3>
              </div>
              <p className="mt-2 text-sm text-muted-foreground">
                Sign in to manage billing and support in-app.
              </p>
              <Button asChild variant="outline" className="mt-4">
                <a href={app("/")}>Log in</a>
              </Button>
            </Card>
          </div>
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

