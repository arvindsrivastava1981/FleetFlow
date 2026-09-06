// Shared brand identity for the public marketing site.
// Truck mark + "VahanKhata.in" wordmark, themed against the shadcn token set
// (bg-primary / text-foreground) so it stays consistent with the rest of the
// marketing chrome.

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

export function BrandMark({ className = "h-8 w-8" }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-flex shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground ${className}`}
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

export default function Logo({ className = "text-lg" }) {
  return (
    <span className="flex items-center gap-2">
      <BrandMark />
      <span
        className={`whitespace-nowrap font-extrabold tracking-tight text-foreground ${className}`}
      >
        VahanKhata<span className="text-primary">.in</span>
      </span>
    </span>
  );
}
