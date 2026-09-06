// Reusable "footer" dock that surfaces the active keyboard shortcuts on data
// entry screens. Each item = { keys: string[] (single key or chord), label }.
// Renders as a sticky bottom bar + <kbd> chips so power users learn the keys.
export default function ShortcutBar({ items }) {
  if (!items?.length) return null;
  return (
    <div
      role="note"
      aria-label="Keyboard shortcuts"
      className="sticky bottom-2 z-10 flex flex-wrap items-center gap-x-4 gap-y-1 rounded-xl border border-ink-100 bg-white/90 px-4 py-2 text-[11px] font-medium text-ink-500 shadow-sm backdrop-blur"
    >
      <span aria-hidden="true">⌨️</span>
      {items.map((it, i) => (
        <span key={i} className="flex items-center gap-1.5">
          {(Array.isArray(it.keys) ? it.keys : [it.keys]).map((k) => (
            <kbd
              key={k}
              className="rounded border border-ink-200 bg-ink-50 px-1.5 py-0.5 text-[10px] font-bold text-ink-700"
            >
              {k}
            </kbd>
          ))}
          <span>{it.label}</span>
        </span>
      ))}
    </div>
  );
}