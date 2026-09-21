import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

const host = document.getElementById("root");
if (!host) {
  throw new Error("console root element is missing from the served document");
}
createRoot(host).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
