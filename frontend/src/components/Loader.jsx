// Reusable loading indicator for initial data fetches. Renders a centered
// spinner + label matching the app's ink/brand palette. Accepts an optional
// `label` (defaults to a generic message) and `full` to make it fill height.
export default function Loader({ label = "Loading…", full = false }) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 ${
        full ? "min-h-[60vh]" : "py-12"
      }`}
    >
      <div className="h-9 w-9 animate-spin rounded-full border-4 border-ink-200 border-t-brand-600" />
      <p className="text-sm text-ink-500">{label}</p>
    </div>
  );
}
