import React from "react";
import Seo from "../Seo";
import { PageHero, CTABand } from "../UI";

const GROUPS = [
  {
    title: "Trip management · ट्रिप मैनेजमेंट",
    icon: "🚚",
    items: [
      "ओडोमीटर के साथ ट्रिप शुरू, पूरी और सेटल",
      "हर गाड़ी का ट्रिप कोड अपने आप",
      "गाड़ी के नंबर से राज्य की पहचान",
      "सेटलमेंट पर ड्राइवर की सहमति दर्ज",
    ],
  },
  {
    title: "Expense & fuel control · ईंधन कंट्रोल",
    icon: "📊",
    items: [
      "ड्राइवर सीधे WhatsApp पर रसीद भेजें",
      "राज्य-वार ईंधन/DEF रेट तुलना (लाइव)",
      "महँगा या गलत रूट का ईंधन अपने आप फ्लैग",
      "एक टैप में मंज़ूरी या कटौती",
    ],
  },
  {
    title: "Driver salary · ड्राइवर सैलरी",
    icon: "⚖️",
    items: [
      "फिक्स्ड, प्रति-किमी, रोज़ाना या शून्य — जैसा चाहें",
      "ट्रिप शुरू होते ही एडवांस लेजर में",
      "सेटलमेंट पर सैलरी अपने आप दर्ज",
      "ड्राइवर अपना हिसाब खुद देख सकता है",
    ],
  },
  {
    title: "Safety & alerts · सुरक्षा",
    icon: "🛡️",
    items: [
      "QR टैग से सुरक्षित इमरजेंसी अलर्ट",
      "फालतू स्कैन से बचाव (anti-spam)",
      "ऑडिट के लिए ड्राइवर सहमति रिकॉर्ड",
    ],
  },
  {
    title: "Fleet & users · फ्लीट और टीम",
    icon: "🏢",
    items: [
      "मल्टी-फ्लीट और मल्टी-मैनेजर ऐक्सेस",
      "हर फर्म के लिए गाड़ी, ड्राइवर, बेंचमार्क",
      "सुपर-एडमिन बनाम मैनेजर अलग नज़र",
    ],
  },
  {
    title: "Billing & reports · बिलिंग रिपोर्ट",
    icon: "💳",
    items: [
      "Razorpay सब्सक्रिप्शन और फ्लीट बिलिंग",
      "सेटल्ड ट्रिप और सैलरी PDF रिपोर्ट",
      "हर बदलाव का ऑडिट लेजर",
    ],
  },
];

export default function Features() {
  return (
    <>
      <Seo
        title="Features — Fleet & Trip Management Platform"
        description="Explore VahanKhata's features: WhatsApp expense intake, per-state fuel benchmarking, driver salary settlement, trip management, emergency alerts, and Razorpay billing."
        path="/features"
      />
      <PageHero
        eyebrow="Features · फीचर्स"
        title="One platform, every rupee on the road accounted for."
        lead="ड्राइवर की रसीद से लेकर ट्रिप सेटलमेंट तक — सब कुछ ट्रैक, बेंचमार्क और साफ़।"
      />

      <section className="market-section market-wrap">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {GROUPS.map((g) => (
            <div key={g.title} className="market-card-hover p-6">
              <span className="text-2xl">{g.icon}</span>
              <h3 className="mt-3 text-lg font-bold text-ink-900">{g.title}</h3>
              <ul className="mt-3 space-y-2">
                {g.items.map((it) => (
                  <li key={it} className="flex items-start gap-2 text-sm leading-relaxed text-ink-600">
                    <span className="mt-0.5 text-brand-600">✓</span>
                    {it}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-12 text-center">
          <a href="/pricing" className="market-btn market-btn-brand">
            See pricing
          </a>
        </div>
      </section>

      <CTABand />
    </>
  );
}