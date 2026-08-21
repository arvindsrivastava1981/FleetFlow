import React, { useState } from "react";
import Seo from "../Seo";
import { PageHero, CTABand } from "../UI";

const FAQS = [
  {
    q: "Do drivers need to install an app? · कोई ऐप चाहिए?",
    a: "नहीं। ड्राइवर ईंधन/रसीद की फोटो सीधे WhatsApp पर भेजता है — VahanKhata खुद पढ़ता है, बेंचमार्क करता है और मंज़ूरी के लिए आगे भेजता है।",
  },
  {
    q: "How does salary settlement work? · सेटलमेंट कैसे?",
    a: "हर ड्राइवर का प्रोफ़ाइल सेट करें (फिक्स्ड, प्रति-किमी, रोज़ाना या शून्य)। ट्रिप शुरू होते ही एडवांस लेजर में; सेटलमेंट पर ड्राइवर की सहमति और सैलरी अपने आप दर्ज — साफ़, ऑडिटेबल रिकॉर्ड।",
  },
  {
    q: "Will it catch fuel overbilling? · ज़्यादा दाम पकड़ेगा?",
    a: "हाँ। हर पेट्रोल/DEF खरीद राज्य के रेट से तुलना होती है — ऊपर का हर खर्च अपने आप फ्लैग और मैनेजर की मंज़ूरी में रुक जाता है।",
  },
  {
    q: "We run multiple fleets. Does it scale? · कई फ्लीट हैं?",
    a: "हाँ — मल्टी-फ्लीट और मल्टी-मैनेजर रोल-बेस्ड ऐक्सेस: सुपर-एडमिन सब देखता है, हर मैनेजर सिर्फ अपनी फर्म का।",
  },
  {
    q: "Is our data secure? · डेटा सुरक्षित है?",
    a: "हर रोल का अलग ऐक्सेस, समय-सीमित सेशन और हर बदलाव का ऑडिट लेजर। Security पेज पर पूरी जानकारी।",
  },
  {
    q: "How does billing and trial work? · बिलिंग कैसे?",
    a: "एक गाड़ी पर 15 दिन फ्री ट्रायल। फिर Monthly (₹799) या Yearly (₹7,191 — 25% छूट), Razorpay से — जब चाहें एक्स्ट्रा गाड़ी स्लॉट जोड़ें।",
  },
  {
    q: "Can drivers see their own earnings? · ड्राइवर देख सकता है?",
    a: "हाँ — ड्राइवर को सिर्फ देखने के लिए अपनी सैलरी/सेटल्ड ट्रिप रसीदें दिखती हैं, जिससे भरोसा बढ़ता है और बहस घटती है।",
  },
];

function FaqItem({ q, a, open, onToggle }) {
  return (
    <div className="market-card overflow-hidden">
      <button
        className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
        onClick={onToggle}
        aria-expanded={open}
      >
        <span className="font-semibold text-ink-900">{q}</span>
        <span className={`text-lg text-brand-600 transition-transform ${open ? "rotate-45" : ""}`}>+</span>
      </button>
      {open && <p className="px-5 pb-5 text-sm leading-relaxed text-ink-600">{a}</p>}
    </div>
  );
}

export default function Faq() {
  const [open, setOpen] = useState(null);
  return (
    <>
      <Seo
        title="FAQ"
        description="Answers to common questions about VahanKhata: WhatsApp expense intake, driver salary settlement, fuel benchmarking, security, multi-fleet support and billing."
        path="/faq"
      />
      <PageHero
        eyebrow="FAQ"
        title="Questions, answered."
        lead="आपके सारे सवाल — आसान भाषा में। और कुछ पूछना हो तो हमसे बात करें।"
      />

      <section className="market-section market-wrap">
        <div className="mx-auto max-w-2xl space-y-3">
          {FAQS.map((f, i) => (
            <FaqItem
              key={f.q}
              q={f.q}
              a={f.a}
              open={open === i}
              onToggle={() => setOpen(open === i ? null : i)}
            />
          ))}
        </div>
        <div className="mt-10 text-center">
          <a href="/contact" className="market-btn market-btn-brand">
            Ask us directly
          </a>
        </div>
      </section>

      <CTABand />
    </>
  );
}