import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Built as a static SPA. The backend (FastAPI) mounts the `dist/` output at "/"
// with an SPA fallback so client-side routes resolve without 404s. All API calls
// use relative `/api/v1/*` paths to stay same-origin (single Render container).
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        // Deterministic asset names simplify long-term CDN caching.
        entryFileNames: "assets/[name]-[hash].js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
  },
  server: {
    // During development, proxy /api to the local FastAPI backend.
    proxy: {
      "/api": "http://localhost:10000",
    },
  },
});