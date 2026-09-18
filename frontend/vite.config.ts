import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The UI talks to the same FastAPI app on the same origin. No second API.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/v1": "http://localhost:8000", "/health": "http://localhost:8000" } },
});
