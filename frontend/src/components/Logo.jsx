// Shared brand identity for the app SPA.
// A fleet-themed truck mark on a gradient tile plus the "VahanKhata.in"
// wordmark. The `.in` TLD is tinted with the brand accent so the renamed
// brand reads clearly at a glance.

const TRUCK_PATHS = (
  <>
    <path d="M14 18V6a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v11a1 1 0 0 0 1 1h2" />
    <path d="M15 18H9" />
    <path d="M19 18h2a1 1 0 0 0 1-1v-3.65a1 1 0 0 0-.22-.624l-3.48-4.35A1 1 0 0 0 17.52 8H14" />
    <circle cx="17" cy="18" r="2" />
    <circle cx="7" cy="18" r="2" />
    <path d="M8 8h2" />
  </>
);

export function BrandMark({
  className = "h-9 w-9",
  tileClassName = "bg-gradient-to-br from-brand-600 to-brand-500",
}) {
  return (
    <span
      aria-hidden="true"
      className={`inline-flex shrink-0 items-center justify-center rounded-xl text-white shadow-sm ${tileClassName} ${className}`}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="h-[58%] w-[58%]"
      >
        {TRUCK_PATHS}
      </svg>
    </span>
  );
}

export default function Logo({
  showTagline = true,
  tagline = "Fleet Expense Verification & Settlement",
  markClassName = "h-9 w-9",
}) {
  return (
    <div className="flex items-center gap-3">
      <BrandMark className={markClassName} />
      <div className="leading-tight">
        <span className="whitespace-nowrap text-base font-extrabold tracking-tight text-ink-900">
          VahanKhata<span className="text-brand-600">.in</span>
        </span>
        {showTagline && (
          <span className="hidden text-[11px] font-medium text-ink-400 sm:block">
            {tagline}
          </span>
        )}
      </div>
    </div>
  );
}
