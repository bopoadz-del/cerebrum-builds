/**
 * Resident engineer panel: the platform's own health, the vendor-slice
 * blockers it is running with, and the alert outbox.
 *
 * Written by the factory WRITER role (codewhale exec)
 */
import React, { useCallback, useEffect, useState } from "react";
import { Json, health, notificationOutbox, vendorHealth } from "../api";

type Health = { ok?: boolean; status?: string; checks?: Array<{ name: string; ok: boolean; detail: string }> };

export default function ResidentEngineer(): JSX.Element {
  const [report, setReport] = useState<Health | null>(null);
  const [vendor, setVendor] = useState<Json | null>(null);
  const [outbox, setOutbox] = useState<Json[]>([]);
  const [error, setError] = useState<string>("");

  const load = useCallback(async () => {
    try {
      setReport((await health()) as Health);
      setVendor(await vendorHealth());
      const alerts = await notificationOutbox();
      setOutbox(alerts.items || []);
      setError("");
    } catch (exc) {
      setError((exc as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const unavailable = (vendor?.unavailable as string[]) || [];
  const defects = (vendor?.known_defects_not_bound as Record<string, string>) || {};

  return (
    <section className="resident-engineer">
      <h2>Resident engineer</h2>
      <button onClick={load}>Refresh</button>
      {error ? <p className="error">{error}</p> : null}
      <h3>Health</h3>
      <ul>
        {(report?.checks || []).map((check) => (
          <li key={check.name} className={check.ok ? "ok" : "bad"}>
            {check.name}: {check.detail}
          </li>
        ))}
      </ul>
      <h3>Vendor slices</h3>
      {unavailable.length ? (
        <p className="bad">Bound but unavailable: {unavailable.join(", ")}</p>
      ) : (
        <p className="ok">Every block this platform binds loads.</p>
      )}
      <ul>
        {Object.entries(defects).map(([block_id, reason]) => (
          <li key={block_id} className="bad">
            <strong>{block_id}</strong>: {reason}
          </li>
        ))}
      </ul>
      <h3>Alert outbox</h3>
      <p>
        Alerts recorded while the Store notify slice is unavailable. A record here is the intent,
        never a claim of delivery.
      </p>
      <ul>
        {outbox.map((alert) => (
          <li key={String(alert.id)}>
            {String(alert.created_at)} {String(alert.capability)}: {String(alert.message)}
          </li>
        ))}
      </ul>
    </section>
  );
}
