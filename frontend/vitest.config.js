import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Audit E-4: frontend test harness (Vitest + Testing Library, jsdom).
export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.js",
    include: ["src/**/*.{test,spec}.{js,jsx}"],
  },
});
