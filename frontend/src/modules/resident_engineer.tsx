// Resident engineer: what this deployment really is, and what it cannot do.
import { useEffect, useState } from "react";

import { vendorHealth } from "../api";

export default function ResidentEngineer() {
  const [health, setHealth] = useState<{ ok: boolean; unavailable: string[] } | null>(null);
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    void (async () => {
      setHealth(await vendorHealth());
      const response = await fetch("/v1/llm", {
        headers: { Authorization: `Bearer ${localStorage.getItem("front-desk-token") || ""}` },
      });
      setStatus(await response.json());
    })();
  }, []);

  return (
    <article className="resident-engineer">
      <h2>Resident engineer</h2>
      <dl>
        <dt>Bound blocks available</dt>
        <dd>{health ? (health.ok ? "yes" : health.unavailable.join(", ")) : "checking"}</dd>
        <dt>Answer engine</dt>
        <dd>{status ? String(status.engine) : "checking"}</dd>
        <dt>Network</dt>
        <dd>{status ? String(status.network) : "checking"}</dd>
      </dl>
      <p>
        Two vendored slices in this checkout cannot load (notification, knowledge).
        They are named on GET /v1/vendor_health and in docs/blockers.json, and no
        capability binds them.
      </p>
    </article>
  );
}
