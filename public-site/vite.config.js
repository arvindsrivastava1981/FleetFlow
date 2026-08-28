import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Standalone static marketing site. The contact form POSTs to the backend
// JSON API (`POST /api/v1/contact`); all other pages are static. The Vite dev
// server proxies `/api` to the local FastAPI backend so local development does
// not need CORS. In production `VITE_API_URL` (https://api.vahankhata.in) is
// used as the absolute origin.
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
  server: {
    proxy: {
      "/api": "http://localhost:10000",
    },
  },
});