import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The platform serves ONE UI at "/", from app/static/. A build writes the
// bundle there so the served console and the typed source cannot drift.
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "../app/static",
    emptyOutDir: false,
    assetsDir: "assets",
  },
});
