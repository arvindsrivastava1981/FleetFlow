import React from "react";
import Seo from "../Seo";
import { PageHero, CTABand, IconChip } from "../UI";
import { LedgerTick } from "../Illustrations";

const REASONS = [
  ["📊", "Per-state fuel benchmarking · ईंधन जाँच", "बाक़ी tools सिर्फ खर्च लिखते हैं — VahanKhata हर पेट्रोल की राज्य-वार रेट से जाँच करता है; ज़्यादा दाम उसी वक़्त फ्लैग।"],
  ["💬", "WhatsApp the drivers already use · WhatsApp ही तो", "कोई ऐप नहीं, ट्रेनिंग नहीं। ड्राइवर फोटो भेजता है; VahanKhata पढ़ता, जाँचता और आगे भेजता है — दिनों में अपनाना शुरू।"],
  ["⚖️", "Salary without battles · बिना बहस सैलरी", "फिक्स्ड, प्रति-किमी या रोज़ाना नियम अपने आप सेटल — ड्राइवर अपने आँकड़े खुद देखता है, महीने की बहस खत्म।"],
  ["🧾", "Cash advances stay traceable · एडवांस का हिसाब", "एडवांस ट्रिप शुरू होते ही लेजर में, सेटलमेंट पर मिलान — 'किसके पास कितना' सवाल ही नहीं।"],
  ["🛡️", "Fraud checks built in · गड़बड़ी पकड़", "टैंक क्षमता, माइलेज और FASTag टोल की अपने आप जाँच — झूठा खर्च सेटलमेंट से पहले फ्लैग।"],
  ["🏢", "Scales with your firm · आपके साथ बढ़े", "एक फ्लीट हो या कई शाखाएँ — मल्टी-फ्लीट, मल्टी-मैनेजर और Razorpay बिलिंग शामिल।"],
];

export default function WhyUs() {
  return (
    <>
      <Seo
        title="Why Us — Compared to Spreadsheets & Other Fleet Tools"
        description="See why transport firms choose VahanKhata over spreadsheets and ERP-style fleet software: live fuel benchmarking, WhatsApp intake, fair driver salary and a full audit trail."
        path="/why-us"
      />
      <PageHero
        eyebrow="Why VahanKhata"
        title="Spreadsheets didn't scale. Neither will a heavyweight ERP."
        lead="VahanKhata वही खूबी है — ड्राइवर का WhatsApp और मालिक का पक्का हिसाब, एक साथ।"
      />

      <section className="market-section market-wrap">
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {REASONS.map(([icon, title, text]) => (
            <div key={title} className="market-card-hover p-6">
              <IconChip>{icon}</IconChip>
              <h3 className="mt-4 text-lg font-bold text-ink-900">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-600">{text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* COMPARISON */}
      <section className="market-section market-wrap border-t border-ink-100">
        <div className="flex flex-col items-center">
          <span className="market-eyebrow">Side by side · तुलना</span>
          <h2 className="market-title">
            Where VahanKhata wins.
            <span className="mt-1 block text-xl font-semibold text-ink-500">VahanKhata कहाँ बेहतर है।</span>
          </h2>
        </div>
        <div className="market-card mt-12 overflow-hidden">
          <div className="hidden grid-cols-3 border-b border-ink-200 bg-ink-50 px-6 py-3 text-sm font-bold text-ink-700 sm:grid">
            <span className="col-span-2">Capability</span>
            <span className="text-brand-600">VahanKhata</span>
          </div>
          {[
            ["लाइव ईंधन जाँच — महीने के आख़िर का झटका नहीं", "✅"],
            ["ड्राइवर WhatsApp पर — ज़ीरो ट्रेनिंग", "✅"],
            ["सैलरी और एडवांस सेटलमेंट अपने आप", "✅"],
            ["ट्रिप शुरू से सेटल तक पूरा ऑडिट", "✅"],
            ["भारतीय फ्लीट ऑपरेशन और बिलिंग के लिए बना", "✅"],
          ].map(([text, mark]) => (
            <div key={text} className="grid grid-cols-3 gap-2 border-b border-ink-100 px-6 py-4 text-sm last:border-b-0">
              <span className="col-span-2 text-ink-700">{text}</span>
              <span className="font-bold text-emerald-600">{mark}</span>
            </div>
          ))}
        </div>
        <LedgerTick className="mx-auto mt-12 w-full max-w-md rounded-3xl shadow-pop" />
        <div className="mt-8 text-center">
          <a href="/request-demo" className="market-btn market-btn-brand">
            See it on a live demo · लाइव डेमो देखें
          </a>
        </div>
      </section>

      <CTABand />
    </>
  );
}