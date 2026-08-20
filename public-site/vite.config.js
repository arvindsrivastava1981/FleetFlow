import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Standalone static marketing site. It has NO API dependency (the contact form
// builds a mailto:/WhatsApp link client-side), so there is no dev proxy and no
// env beyond VITE_APP_URL (used by src/config.js to build app login links).
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        entryFileNames: "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
});