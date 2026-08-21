import React from "react";
import Seo from "../Seo";
import { PageHero, CTABand, IconChip } from "../UI";
import { TruckRoad } from "../Illustrations";

const VALUES = [
  ["🎯", "Clarity over chaos · साफ़ हिसाब", "पैसा कहाँ गया — अंदाज़ा नहीं, पूरा हिसाब। हर ट्रिप, लीटर और रुपये का लाइव लेजर।"],
  ["⚖️", "Fairness for drivers · ड्राइवर के साथ ईमानदारी", "साफ़ सैलरी और सेटलमेंट से ड्राइवर को भरोसा — और भरोसा टिकता है।"],
  ["📉", "Stop silent leakage · छुपा नुकसान बंद", "ज़्यादा ईंधन बिल और खोए चालान — हम सबसे पहले पकड़ते हैं।"],
  ["🚚", "Built for the road · रोड के लिए बना", "WhatsApp पहले — ड्राइवर हाईवे पर है, दफ़्तर में नहीं।"],
];

export default function About() {
  return (
    <>
      <Seo
        title="About Us"
        description="VahanKhata exists to give Indian transport firms a single, honest view of every trip — from fuel to salary settlement. Meet the team and mission."
        path="/about"
      />
      <PageHero
        eyebrow="Our story · हमारी कहानी"
        title="We live where the fleet does."
        lead="बिना हिसाब की WhatsApp रसीदें और कॉपी में लिखे हिसाब ने फर्मों की कमाई खाई — VahanKhata उही लड़ाई से बना है।"
      />

      {/* MISSION */}
      <section className="market-section market-wrap">
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <div>
            <span className="market-eyebrow">Our mission · हमारा मक़सद</span>
            <h2 className="market-title">
              Every rupee accounted for. Every driver treated fairly.
              <span className="mt-1 block text-xl font-semibold text-ink-500">हर रुपये का हिसाब, हर ड्राइवर के साथ इंसाफ़।</span>
            </h2>
            <p className="mt-5 text-base leading-relaxed text-ink-600">
              भारत का ट्रांसपोर्ट भरोसे पर चलता है — हम उस भरोसे को रिकॉर्ड देते हैं। VahanKhata WhatsApp की आसानी और
              कड़क ईंधन-बेंचमार्किंग को जोड़ता है, ताकि मालिक की कमाई बढ़े और ड्राइवर को साफ़ सौदा मिले।
            </p>
          </div>
          <div>
            <TruckRoad className="w-full rounded-3xl shadow-pop" />
            <div className="mt-4 grid grid-cols-3 gap-3">
              {[
                { k: "1", v: "WhatsApp-first" },
                { k: "50+", v: "fuel benchmarks" },
                { k: "0", v: "spreadsheets" },
              ].map((s) => (
                <div key={s.v} className="rounded-xl bg-white p-3 text-center shadow-sm border border-ink-100">
                  <p className="text-xl font-black text-brand-600">{s.k}</p>
                  <p className="mt-1 text-[11px] font-semibold text-ink-500">{s.v}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* VALUES */}
      <section className="market-section market-wrap border-t border-ink-100">
        <div className="flex flex-col items-center">
          <span className="market-eyebrow">What we stand for · हमारे उसूल</span>
          <h2 className="market-title">
            Values that drive every build.
            <span className="mt-1 block text-xl font-semibold text-ink-500">हर फैसला इन्हीं कीमतों पर।</span>
          </h2>
        </div>
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {VALUES.map(([icon, title, text]) => (
            <div key={title} className="market-card-hover p-6">
              <IconChip>{icon}</IconChip>
              <h3 className="mt-4 text-base font-bold text-ink-900">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-600">{text}</p>
            </div>
          ))}
        </div>
      </section>

      <CTABand title="Let's build cleaner fleets together." />
    </>
  );
}