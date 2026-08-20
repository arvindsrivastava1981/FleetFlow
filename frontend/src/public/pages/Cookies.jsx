import React from "react";
import Seo from "../Seo";
import { PageHero, Prose } from "../UI";

export default function Cookies() {
  return (
    <>
      <Seo
        title="Cookie Policy — FleetFlow"
        description="How FleetFlow uses cookies and similar technologies for authentication, security and analytics."
        path="/cookies"
      />
      <PageHero eyebrow="Legal" title="Cookie Policy" lead="Last updated: August 2026" />
      <Prose>
        <p>
          This Cookie Policy explains how FleetFlow uses cookies and similar technologies when you visit our site or
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
          Questions about cookies? Email <a href="mailto:hello@fleetflow.app">hello@fleetflow.app</a>.
        </p>
      </Prose>
    </>
  );
}