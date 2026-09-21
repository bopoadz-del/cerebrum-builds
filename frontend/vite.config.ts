import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * The console is served by the platform itself (app/static), so the dev server
 * proxies /v1 to a locally running uvicorn: `uvicorn app.main:app --port 8000`.
 */
export default defineConfig({
  plugins: [react()],
  build: { outDir: "../app/static", emptyOutDir: false },
  server: {
    port: 5173,
    proxy: {
      "/v1": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/metrics": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
