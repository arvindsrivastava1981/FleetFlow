import React from "react";
import Seo from "../Seo";
import { PageHero, Prose, HiNote } from "../UI";

export default function Cookies() {
  return (
    <>
      <Seo
        title="Cookie Policy"
        description="How VahanKhata uses cookies and similar technologies for authentication, security and analytics."
        path="/cookies"
      />
      <PageHero eyebrow="Legal" title="Cookie Policy" lead="Last updated: August 2026" />
      <HiNote>
        हम कम से कम कुकीज़ इस्तेमाल करते हैं — साइन-इन और सुरक्षा के लिए ज़रूरी कुकीज़ हमेशा लगती हैं, एनालिटिक्स सिर्फ
        आपकी मर्ज़ी से। विज्ञापन या क्रॉस-साइट ट्रैकिंग कुकीज़ नहीं।
      </HiNote>
      <Prose>
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
          Questions about cookies? Email <a href="mailto:hello@vahankhata.in">hello@vahankhata.in</a>.
        </p>
      </Prose>
    </>
  );
}