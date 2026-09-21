/**
 * Resident engineer: the operator's own view of the deployment.
 *
 * Reads the platform's health and metrics endpoints and shows what the
 * container is doing -- process, persistent disk, database, migrations, and the
 * request counters the /metrics route serves. It exists so the person who
 * deploys this can answer "is it up, is it slow" without reading logs, and it
 * reports a not-ready body as a failure rather than pretending.
 */
import { useEffect, useState } from "react";

interface HealthCheck {
  name: string;
  ok: boolean;
  detail?: string;
}

export default function ResidentEngineer() {
  const [health, setHealth] = useState<{ status?: string; checks?: HealthCheck[] } | null>(null);
  const [metrics, setMetrics] = useState<string>("");

  useEffect(() => {
    let live = true;
    async function poll() {
      const healthResponse = await fetch("/health");
      const metricsResponse = await fetch("/metrics");
      if (!live) return;
      setHealth(healthResponse.ok ? await healthResponse.json() : { status: `HTTP ${healthResponse.status}` });
      const text = await metricsResponse.text();
      setMetrics(text.split("\n").slice(0, 12).join("\n"));
    }
    void poll();
    const timer = setInterval(() => void poll(), 15000);
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, []);

  return (
    <section style={{ marginTop: 24 }}>
      <h2 style={{ fontSize: 16 }}>Resident engineer</h2>
      <p>health: {health ? health.status : "…"}</p>
      <ul>
        {(health?.checks || []).map((check) => (
          <li key={check.name} style={{ color: check.ok ? "inherit" : "#a3282f" }}>
            {check.name}: {check.ok ? "ok" : "not ok"} {check.detail ? `— ${check.detail}` : ""}
          </li>
        ))}
      </ul>
      <pre style={{ maxHeight: 200, overflow: "auto" }}>{metrics}</pre>
    </section>
  );
}
