import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // The bundle is mounted at /console (Dockerfile: COPY --from=console
  // /ui/dist /app/frontend-dist; app/main.py: mount("/console", ...)). Vite's
  // default base emits asset URLs like /assets/index-*.js, which nothing
  // serves at the root — the page would load and then 404 its own JavaScript.
  base: "/console/",
  build: { outDir: "dist", emptyOutDir: true },
});
