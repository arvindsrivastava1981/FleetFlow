import React, { useState } from "react";
import Seo from "../Seo";
import { PageHero } from "../UI";
import { app } from "../../config.js";

const CONTACT_EMAIL = "hello@fleetflow.app";

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

  const whatsappLink = `https://wa.me/919999999999?text=${encodeURIComponent(
    `Hi FleetFlow, I'd like a demo. (${form.name || "Inquiry"})`
  )}`;

  return (
    <>
      <Seo
        title="Contact Us — FleetFlow"
        description="Talk to the FleetFlow team about a demo, pricing or onboarding. Reach us by email or WhatsApp."
        path="/contact"
      />
      <PageHero
        eyebrow="Contact"
        title="Let's talk about your fleet."
        lead="Book a demo, ask a pricing question, or get help setting up — we usually reply within one business day."
      />

      <section className="market-section market-wrap">
        <div className="grid gap-10 lg:grid-cols-2">
          {/* Form */}
          <div className="market-card p-6 sm:p-8">
            <h2 className="text-lg font-bold text-ink-900">Send us a message</h2>
            {sent ? (
              <div className="mt-6 rounded-xl bg-emerald-50 p-6 text-center">
                <p className="text-lg font-bold text-emerald-700">✅ Almost there!</p>
                <p className="mt-2 text-sm text-emerald-800">
                  Your email app should open with our message pre-filled. Hit send and we'll be in touch.
                </p>
                <button className="mt-4 market-btn market-btn-ghost" onClick={() => setSent(false)}>
                  Write another
                </button>
              </div>
            ) : (
              <form
                className="mt-6 space-y-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  window.location.href = buildMailto();
                  setSent(true);
                }}
              >
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="label">Your name *</label>
                    <input className="input" required value={form.name} onChange={update("name")} placeholder="Rajesh Kumar" />
                  </div>
                  <div>
                    <label className="label">Company / fleet</label>
                    <input className="input" value={form.firm} onChange={update("firm")} placeholder="Your firm" />
                  </div>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="label">Email *</label>
                    <input className="input" required type="email" value={form.email} onChange={update("email")} placeholder="you@firm.com" />
                  </div>
                  <div>
                    <label className="label">Phone</label>
                    <input className="input" value={form.phone} onChange={update("phone")} placeholder="+91 …" />
                  </div>
                </div>
                <div>
                  <label className="label">Message *</label>
                  <textarea
                    className="input min-h-28"
                    required
                    value={form.message}
                    onChange={update("message")}
                    placeholder="How many vehicles and drivers do you run?"
                  />
                </div>
                <button type="submit" className="market-btn market-btn-brand w-full">
                  Send message
                </button>
              </form>
            )}
          </div>

          {/* Contact details */}
          <div className="space-y-4">
            <div className="market-card-hover p-6">
              <h3 className="flex items-center gap-2 text-lg font-bold text-ink-900">📧 Email</h3>
              <a href={`mailto:${CONTACT_EMAIL}`} className="mt-1 inline-block text-brand-600">
                {CONTACT_EMAIL}
              </a>
            </div>
            <div className="market-card-hover p-6">
              <h3 className="flex items-center gap-2 text-lg font-bold text-ink-900">💬 WhatsApp</h3>
              <p className="mt-1 text-sm text-ink-600">Fastest for a quick demo request.</p>
              <a href={whatsappLink} className="market-btn market-btn-brand mt-4">
                Message on WhatsApp
              </a>
            </div>
            <div className="market-card-hover p-6">
              <h3 className="flex items-center gap-2 text-lg font-bold text-ink-900">💳 Billing & support</h3>
              <p className="mt-1 text-sm leading-relaxed text-ink-600">
                Already a customer? Sign in and use the in-app change-password or reach the operations team for billing.
              </p>
              <a href={app("/login")} className="market-btn market-btn-ghost mt-4">
                Log in
              </a>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}