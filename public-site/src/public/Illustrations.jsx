/**
 * Flat inline-SVG illustrations of transport-industry pain points, drawn in
 * the site's brand palette. Inline components (not image files) keep the
 * static bundle tiny and license-clean. To use real fleet photos instead,
 * replace the <PaperChaos /> etc. usage with an <img src="/img/..." />.
 */

export function PaperChaos({ className = "" }) {
  return (
    <svg viewBox="0 0 320 220" className={className} role="img" aria-label="Scattered paper receipts and unwatched WhatsApp chats">
      <rect width="320" height="220" rx="20" fill="#eef2ff" />
      <g transform="rotate(-12 75 120)">
        <rect x="40" y="70" width="72" height="98" rx="6" fill="#ffffff" stroke="#cbd5e1" />
        <rect x="50" y="84" width="52" height="6" rx="3" fill="#e2e8f0" />
        <rect x="50" y="98" width="38" height="6" rx="3" fill="#e2e8f0" />
        <rect x="50" y="112" width="46" height="6" rx="3" fill="#e2e8f0" />
        <rect x="50" y="138" width="32" height="12" rx="3" fill="#f59e0b" />
      </g>
      <g transform="rotate(10 245 150)">
        <rect x="205" y="105" width="72" height="98" rx="6" fill="#ffffff" stroke="#cbd5e1" />
        <rect x="215" y="119" width="52" height="6" rx="3" fill="#e2e8f0" />
        <rect x="215" y="133" width="40" height="6" rx="3" fill="#e2e8f0" />
        <rect x="215" y="147" width="48" height="6" rx="3" fill="#e2e8f0" />
        <rect x="215" y="173" width="32" height="12" rx="3" fill="#f43f5e" />
      </g>
      <rect x="128" y="42" width="88" height="152" rx="14" fill="#1e293b" />
      <rect x="136" y="58" width="72" height="122" rx="8" fill="#f1f5f9" />
      <rect x="144" y="68" width="42" height="14" rx="7" fill="#ffffff" stroke="#cbd5e1" />
      <rect x="158" y="90" width="42" height="14" rx="7" fill="#dcfce7" />
      <rect x="144" y="112" width="46" height="26" rx="6" fill="#ffffff" stroke="#cbd5e1" />
      <circle cx="156" cy="121" r="5" fill="#94a3b8" />
      <path d="M150 132 l8 -7 6 5 8 -9" stroke="#94a3b8" strokeWidth="2" fill="none" />
      <circle cx="160" cy="26" r="15" fill="#10b981" />
      <text x="160" y="32" textAnchor="middle" fontSize="16" fontWeight="800" fill="#ffffff">₹</text>
    </svg>
  );
}

export function FuelLeak({ className = "" }) {
  return (
    <svg viewBox="0 0 320 220" className={className} role="img" aria-label="Fuel overbilling draining money">
      <rect width="320" height="220" rx="20" fill="#eef2ff" />
      <rect x="60" y="40" width="86" height="140" rx="10" fill="#4f46e5" />
      <rect x="72" y="54" width="62" height="40" rx="6" fill="#eef2ff" />
      <text x="103" y="81" textAnchor="middle" fontSize="20" fontWeight="800" fill="#4f46e5">₹104</text>
      <rect x="72" y="106" width="62" height="8" rx="4" fill="#a5b4fc" />
      <rect x="72" y="122" width="44" height="8" rx="4" fill="#a5b4fc" />
      <path d="M146 70 h26 v52 a10 10 0 0 1 -20 0" stroke="#334155" strokeWidth="8" fill="none" strokeLinecap="round" />
      <path d="M60 180 h200" stroke="#cbd5e1" strokeWidth="6" strokeLinecap="round" />
      <g fill="#f59e0b">
        <circle cx="196" cy="150" r="11" />
        <circle cx="222" cy="164" r="11" />
        <circle cx="248" cy="148" r="11" />
      </g>
      <g fill="#ffffff" fontSize="12" fontWeight="800" textAnchor="middle">
        <text x="196" y="155">₹</text>
        <text x="222" y="169">₹</text>
        <text x="248" y="153">₹</text>
      </g>
      <path d="M222 128 v14 m0 0 l-6 -6 m6 6 l6 -6" stroke="#f43f5e" strokeWidth="4" strokeLinecap="round" fill="none" />
    </svg>
  );
}

export function TruckRoad({ className = "" }) {
  return (
    <svg viewBox="0 0 320 220" className={className} role="img" aria-label="Truck running on the highway">
      <rect width="320" height="220" rx="20" fill="#eef2ff" />
      <circle cx="268" cy="42" r="18" fill="#fcd34d" />
      <path d="M40 180 h240" stroke="#94a3b8" strokeWidth="10" strokeLinecap="round" />
      <path d="M70 180 h24 m24 0 h24 m24 0 h24 m24 0 h24" stroke="#ffffff" strokeWidth="4" strokeLinecap="round" />
      <rect x="70" y="96" width="120" height="62" rx="8" fill="#c7d2fe" />
      <rect x="190" y="112" width="52" height="46" rx="8" fill="#4f46e5" />
      <rect x="198" y="120" width="24" height="18" rx="4" fill="#e0e7ff" />
      <circle cx="100" cy="162" r="14" fill="#1e293b" />
      <circle cx="100" cy="162" r="6" fill="#94a3b8" />
      <circle cx="216" cy="162" r="14" fill="#1e293b" />
      <circle cx="216" cy="162" r="6" fill="#94a3b8" />
      <g transform="translate(130 30)">
        <path d="M30 44 C14 26 18 4 30 4 s16 22 0 40 z" fill="#f43f5e" transform="rotate(180 30 24)" />
        <circle cx="30" cy="18" r="7" fill="#ffffff" />
      </g>
    </svg>
  );
}

export function LedgerTick({ className = "" }) {
  return (
    <svg viewBox="0 0 320 220" className={className} role="img" aria-label="Clean auditable settlement ledger">
      <rect width="320" height="220" rx="20" fill="#eef2ff" />
      <rect x="58" y="36" width="204" height="148" rx="12" fill="#4f46e5" />
      <rect x="72" y="50" width="176" height="120" rx="8" fill="#ffffff" />
      <g stroke="#e2e8f0" strokeWidth="6" strokeLinecap="round">
        <path d="M86 70 h96" />
        <path d="M86 94 h84" />
        <path d="M86 118 h92" />
        <path d="M86 142 h72" />
      </g>
      <g stroke="#10b981" strokeWidth="5" strokeLinecap="round" fill="none">
        <path d="M196 66 l7 7 13 -14" />
        <path d="M196 90 l7 7 13 -14" />
        <path d="M196 138 l7 7 13 -14" />
      </g>
      <circle cx="209" cy="118" r="10" fill="#f43f5e" />
      <path d="M205 118 h8" stroke="#ffffff" strokeWidth="4" strokeLinecap="round" />
      <circle cx="248" cy="170" r="22" fill="#10b981" />
      <path d="M238 170 l7 7 14 -15" stroke="#ffffff" strokeWidth="5" strokeLinecap="round" fill="none" />
    </svg>
  );
}
