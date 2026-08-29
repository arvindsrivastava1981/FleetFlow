import React, { useState } from "react";
import Seo from "../Seo";
import { Button } from "../../components/ui/button.jsx";
import { Card } from "../../components/ui/card.jsx";
import { Mail, MessageCircle, UserRound, AlertCircle } from "lucide-react";
import { app, api } from "../../config.js";

const CONTACT_EMAIL = "support@vahankhata.in";
const API_PATH = "/api/v1/contact";

const initialForm = { name: "", firm: "", email: "", phone: "", message: "", website: "" };

// Turn the backend's error envelope into a human-readable message. For 422s the
// useful info lives in `details` ([{loc, msg, type}]) while `error` is generic.
const FIELD_LABELS = {
  name: "Name",
  firm: "Firm name",
  email: "Email",
  phone: "Phone",
  message: "Message",
  website: "Website",
};

function extractApiError(data) {
  const fallback = "Something went wrong. Please try again.";
  if (Array.isArray(data?.details) && data.details.length > 0) {
    const parts = data.details.map((d) => {
      const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null;
      const label = FIELD_LABELS[field] || field || "Request";
      const msg = String(d.msg || "").replace(/^Value error,\s*/i, "").trim();
      return msg ? `${label}: ${msg}` : `${label} is invalid.`;
    });
    return parts.join(". ");
  }
  return (
    data?.error ||
    data?.detail ||
    data?.data?.message ||
    fallback
  );
}

export default function Contact() {
  const [form, setForm] = useState(initialForm);
  const [state, setState] = useState("idle"); // "idle" | "submitting" | "sent" | "received" | "error"
  const [errorMsg, setErrorMsg] = useState("");
  const update = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const whatsappLink = `https://wa.me/918860666659?text=${encodeURIComponent(
    `Hi VahanKhata, I'd like a demo. (${form.name || "Inquiry"})`
  )}`;

  const handleSubmit = async (e) => {
    e.preventDefault();
    // Honeypot — bots fill every field, humans don't see it.
    if (form.website) return;
    setErrorMsg("");
    setState("submitting");
    try {
      const res = await fetch(api(API_PATH), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name.trim(),
          email: form.email.trim(),
          phone: form.phone.trim() || undefined,
          firm: form.firm.trim() || undefined,
          message: form.message.trim(),
          website: form.website,
        }),
      });
      // A non-JSON response (e.g. the SPA's index.html, served when
      // VITE_API_URL is missing so the form POSTs to the static site itself)
      // must not be silently reduced to `{}` — surface it honestly.
      const contentType = res.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) {
        setErrorMsg(
          "The contact service is not reachable right now (API endpoint misconfigured). Please email us directly below."
        );
        setState("error");
        return;
      }
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.data?.sent) {
        setState("sent");
      } else if (res.ok && data.data?.sent === false && data.data?.message) {
        // Email transport not configured in this environment (e.g. dev/CI).
        // The submission itself was accepted — show it as a soft notice.
        setErrorMsg(data.data.message);
        setState("received");
      } else {
        setErrorMsg(extractApiError(data));
        setState("error");
      }
    } catch {
      setErrorMsg("Network error. Please check your connection and try again.");
      setState("error");
    }
  };

  const reset = () => {
    setForm(initialForm);
    setState("idle");
    setErrorMsg("");
  };

  // Pre-filled mailto fallback so a failed submission is never a dead end.
  const mailtoFallback = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(
    "VahanKhata enquiry"
  )}&body=${encodeURIComponent(
    `${form.message}\n\n— ${form.name || ""}${form.firm ? `, ${form.firm}` : ""}\n${form.email || ""}`
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
          <p className="mt-1 text-sm leading-relaxed text-muted-foreground" lang="hi">
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
            {state === "sent" ? (
              <div className="rounded-xl bg-emerald-50 p-6 text-center">
                <p className="text-lg font-bold text-emerald-700">Message sent!</p>
                <p className="mt-2 text-sm text-emerald-800">
                  Your message has been sent to {CONTACT_EMAIL}. We'll reply within one business day.
                </p>
                <Button variant="outline" className="mt-4" onClick={reset}>
                  Send another
                </Button>
              </div>
            ) : state === "received" ? (
              <div className="rounded-xl bg-amber-50 p-6 text-center">
                <p className="text-lg font-bold text-amber-700">Message received</p>
                <p className="mt-2 text-sm text-amber-800">{errorMsg}</p>
                <p className="mt-2 text-sm text-amber-800">
                  Need an urgent reply? Email us directly at{" "}
                  <a className="font-semibold underline" href={`mailto:${CONTACT_EMAIL}`}>
                    {CONTACT_EMAIL}
                  </a>
                  .
                </p>
                <Button variant="outline" className="mt-4" onClick={reset}>
                  Send another
                </Button>
              </div>
            ) : (
              <form className="space-y-4" onSubmit={handleSubmit}>
                {/* Honeypot — hidden from humans, filled by bots */}
                <div className="hidden">
                  <label className="sr-only">Leave this field empty</label>
                  <input
                    type="text"
                    value={form.website}
                    onChange={update("website")}
                    autoComplete="off"
                    tabIndex={-1}
                    aria-hidden="true"
                  />
                </div>
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
                {state === "error" && (
                  <div className="rounded-md bg-rose-50 p-3 text-sm text-rose-800">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0" />
                      <span>{errorMsg}</span>
                    </div>
                    <p className="mt-2">
                      Your message is still here — try again, or{" "}
                      <a
                        className="font-semibold underline"
                        href={mailtoFallback}
                        aria-label={`Email your enquiry to ${CONTACT_EMAIL}`}
                      >
                        send it as an email
                      </a>{" "}
                      instead.
                    </p>
                  </div>
                )}

                <Button type="submit" className="w-full" disabled={state === "submitting"}>
                  {state === "submitting" ? "Sending…" : "Send message"}
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
    </>
  );
}

