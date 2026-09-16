/** Vite entry point for the Hotel Front Desk Log UI. */
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

const container = document.getElementById("root");
if (container) {
  createRoot(container).render(<App />);
}
