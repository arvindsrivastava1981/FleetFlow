import { createContext, useContext, useState } from "react";

const ShortcutContext = createContext(null);

export function ShortcutProvider({ children }) {
  const [shortcuts, setShortcuts] = useState([]);

  return (
    <ShortcutContext.Provider value={{ shortcuts, setShortcuts }}>
      {children}
    </ShortcutContext.Provider>
  );
}

export function useShortcuts() {
  const ctx = useContext(ShortcutContext);
  if (!ctx) throw new Error("useShortcuts must be used within ShortcutProvider");
  return ctx;
}

