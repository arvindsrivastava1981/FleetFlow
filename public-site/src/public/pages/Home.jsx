import React from "react";
import Seo from "../Seo";
import { IconChip, CTABand } from "../UI";
import { PaperChaos } from "../Illustrations";

const HERO_PAINS = [
  "ईंधन के बढ़े बिल — ज़्यादा दाम पकड़ने का कोई तरीका नहीं",
  "ड्राइवर रसीदें उस नंबर पर भेजता है जहाँ कोई देखता ही नहीं",
  "सेटलमेंट पर सैलरी और एडवांस की रोज़ की बहस",
  "चालान, मरम्मत और एडवांस कॉपियों में कहीं खो गए",
];

// Stats shown in the hero's mock "VahanKhata Dashboard" card.
const HERO_STATS = [
  { label: "Active trips", value: "1,248", cls: "bg-brand-50" },
  { label: "Expenses logged", value: "₹4.2L", cls: "bg-emerald-50" },
  { label: "Fuel saved", value: "₹38K", cls: "bg-amber-50" },
  { label: "Settled clean", value: "96%", cls: "bg-sky-50" },
];

const FEATURES = [
  ["🧾", "brand", "WhatsApp expense intake · WhatsApp पर खर्च", "ड्राइवर रसीद की फोटो WhatsApp पर भेजता है — VahanKhata खुद पढ़कर महँगा ईंधन पकड़ लेता है।"],
  ["📊", "emerald", "Live fuel benchmarking · ईंधन जाँच", "हर पेट्रोल/DEF खरीद राज्य के रेट से तुरंत तुलना होती है — महीने के आखिर तक इंतज़ार नहीं।"],
  ["🚚", "amber", "Trip start to settlement · ट्रिप हिसाब", "ओडोमीटर से शुरू, सेटलमेंट पर खत्म — एडवांस, सैलरी और सहमति सब अपने आप दर्ज।"],
  ["⚖️", "violet", "Fair driver salary · साफ़ सैलरी", "फिक्स्ड, प्रति-किलोमीटर या रोज़ाना नियम — ड्राइवर को अपना हिसाब साफ़ दिखता है, बहस खत्म।"],
  ["🛡️", "sky", "Emergency alerts & QR · इमरजेंसी", "हर टैग पर QR और सुरक्षित इमरजेंसी अलर्ट — फालतू नॉइज़ नहीं।"],
  ["🏢", "rose", "Made for Indian fleets · भारतीय फ्लीट", "मल्टी-फ्लीट, मल्टी-मैनेजर, ड्राइवर सैलरी और Razorpay बिलिंग — पहले से शामिल।"],
];

function PainItem({ text, i }) {
  return (
    <li className="flex items-start gap-3">
      <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-rose-100 text-xs font-black text-rose-600">
        {i}
      </span>
      <span className="text-sm leading-relaxed text-ink-700">{text}</span>
    </li>
  );
}

const HOW = [
  ["1", "Create the trip · ट्रिप शुरू", "गाड़ी, ड्राइवर और ओडोमीटर भरें — एडवांस अपने आप लेजर में।"],
  ["2", "Driver sends expenses · खर्च आए", "ईंधन/DEF की फोटो WhatsApp पर — तुरंत जाँच और फ्लैग।"],
  ["3", "Manager approves · मंज़ूरी", "एक टैप में मंज़ूर या कटौती — स्प्रेडशीट का काम खत्म।"],
  ["4", "Trip settles · हिसाब पक्का", "ड्राइवर की सहमति, सैलरी दर्ज — रिकॉर्ड हमेशा के लिए लॉक।"],
];

export default function Home() {
  return (
    <>
      <Seo
        title="Smart Fleet Expense & Trip Management for Indian Transport Firms"
        description="VahanKhata.in — live fuel benchmarking, driver salary settlement and trip management for Indian transport firms. ट्रिप का पूरा हिसाब: ईंधन जाँच, ड्राइवर सैलरी और सेटलमेंट एक ही जगह।"
        path="/"
      />

      {/* HERO */}
      <section className="market-band relative overflow-hidden">
        <div className="market-grid absolute inset-0 opacity-60" aria-hidden />
        <div className="market-wrap relative grid items-center gap-10 py-16 sm:py-24 lg:grid-cols-2">
          <div>
            <span className="market-eyebrow !border-white/25 !bg-white/10 !text-brand-100">
              Built for Indian transport firms · भारतीय ट्रांसपोर्ट फर्मों के लिए
            </span>
            <h1 className="mt-5 text-balance text-4xl font-extrabold leading-[1.05] tracking-tight text-white sm:text-5xl lg:text-[3.4rem]">
              Stop bleeding money on{" "}
              <span className="market-grad-text">fuel, salary and unsettled trips.</span>
              <span className="mt-3 block text-balance text-2xl font-bold leading-snug text-brand-100 sm:text-3xl">
                इंधन, सैलरी और अधूरे हिसाब पर पैसा बहाना बंद।
              </span>
            </h1>
            <p className="mt-5 max-w-xl text-pretty text-base leading-relaxed text-brand-100 sm:text-lg">
              हर ट्रिप का पूरा हिसाब एक जगह — WhatsApp रसीद से लेकर सेटलमेंट तक।
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <a href="/request-demo" className="market-btn market-btn-brand !bg-white !text-brand-900 hover:!bg-brand-50">
                Book a free demo
              </a>
              <a href="/pricing" className="market-btn market-btn-dark">
                See pricing
              </a>
            </div>
            <p className="mt-4 text-xs text-brand-200/80">15 दिन का फ्री ट्रायल · कोई क्रेडिट कार्ड नहीं · एक दिन में सेटअप</p>
          </div>

          <div className="market-card p-6">
            <div className="flex items-center gap-3 border-b border-ink-100 pb-4">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600 text-base font-black text-white">
                V
              </span>
              <div>
                <p className="text-sm font-bold text-ink-900">VahanKhata Dashboard</p>
                <p className="text-xs text-ink-500">Live view · trips &amp; expenses</p>
              </div>
              <span className="badge badge-success ml-auto">Live</span>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3">
              {HERO_STATS.map((s) => (
                <div key={s.label} className={`rounded-xl p-4 ${s.cls}`}>
                  <p className="text-[11px] font-bold uppercase tracking-wider text-ink-500">{s.label}</p>
                  <p className="mt-1 text-2xl font-extrabold tracking-tight text-ink-900">{s.value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* PROBLEM */}
      <section className="market-section market-wrap">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <div>
            <span className="market-eyebrow">The problem · समस्या</span>
            <h2 className="market-title">
              Profits leak from small places.
              <span className="mt-1 block text-xl font-semibold text-ink-500">छोटी-छोटी जगहों से कमाई बह जाती है।</span>
            </h2>
            <ul className="mt-6 space-y-3">
              {HERO_PAINS.map((p, i) => (
                <PainItem key={p} text={p} i={i + 1} />
              ))}
            </ul>
          </div>
          <PaperChaos className="w-full max-w-md justify-self-center rounded-3xl shadow-pop" />
        </div>
      </section>

      {/* SOLUTION: FEATURES */}
      <section className="market-section market-wrap border-t border-ink-100">
        <div className="flex flex-col items-center">
          <span className="market-eyebrow">The solution · समाधान</span>
          <h2 className="market-title">
            Every expense, turned into savings.
            <span className="mt-1 block text-xl font-semibold text-ink-500">फ्लीट का हर खर्च, बचत में बदलें।</span>
          </h2>
        </div>
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(([icon, tone, title, text]) => (
            <div key={title} className="market-card-hover p-6">
              <IconChip tone={tone}>{icon}</IconChip>
              <h3 className="mt-4 text-lg font-bold text-ink-900">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-600">{text}</p>
            </div>
          ))}
        </div>
        <div className="mt-10 text-center">
          <a href="/features" className="market-btn market-btn-brand">
            Explore all features
          </a>
        </div>
      </section>

      {/* HOW IT WORKS STRIP */}
      <section className="market-section market-wrap border-t border-ink-100">
        <div className="flex flex-col items-center">
          <span className="market-eyebrow">How it works · ऐसे चलता है</span>
          <h2 className="market-title">
            Trip start to settlement — one thread.
            <span className="mt-1 block text-xl font-semibold text-ink-500">ट्रिप शुरू से सेटलमेंट तक — एक ही जगह।</span>
          </h2>
        </div>
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {HOW.map(([n, t, d]) => (
            <div key={n} className="relative rounded-2xl border border-ink-200 bg-white p-6 shadow-sm">
              <span className="text-4xl font-black text-brand-200">{n}</span>
              <h3 className="mt-3 text-base font-bold text-ink-900">{t}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-600">{d}</p>
            </div>
          ))}
        </div>
      </section>

      <CTABand />
    </>
  );
}