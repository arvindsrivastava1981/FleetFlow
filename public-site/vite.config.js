import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Standalone static marketing site. It has NO API dependency (the contact form
// builds a mailto:/WhatsApp link client-side), so there is no dev proxy.
// "Log in" links are built in src/config.js from the hard-coded app origin.
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