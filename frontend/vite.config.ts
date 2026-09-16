import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The UI talks to the platform's own routes; in dev, proxy them to the API.
export default defineConfig({
  plugins: [react()],
  build: { outDir: "dist", emptyOutDir: true },
  server: {
    proxy: {
      "/v1": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
