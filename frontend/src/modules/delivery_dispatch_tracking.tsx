// Dispatch board — Assigns drivers and vehicles and follows each delivery from pickup to drop-off.
// Written by the factory WRITER role (codewhale exec)
import { useState } from "react";
import { create, list, type CapabilityId, type Record } from "../api";

export default function DeliveryDispatchTracking({ capability }: { capability: CapabilityId }) {
  const [primary, setPrimary] = useState("");
  const [secondary, setSecondary] = useState("sample");
  const [rows, setRows] = useState<Record[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      const body = await list(capability);
      setRows(body.items ?? []);
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "request failed");
    }
  }

  async function submit() {
    const body: Record = {
      reference: primary || "sample",
      order_code: secondary,
      driver_code: secondary,
      status: "open",
    };
    try {
      await create(capability, body);
      await refresh();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "request failed");
    }
  }

  return (
    <section>
      <h2>Dispatch board</h2>
      <p>Assigns drivers and vehicles and follows each delivery from pickup to drop-off.</p>
      <label>
        order_code
        <input value={primary} onChange={(event) => setPrimary(event.target.value)} />
      </label>
      <label>
        driver_code
        <input value={secondary} onChange={(event) => setSecondary(event.target.value)} />
      </label>
      <button onClick={submit}>Record</button>
      <button onClick={refresh}>Refresh</button>
      {error ? <p role="alert">{error}</p> : null}
      <ul>
        {rows.map((row) => (
          <li key={String(row.id)}>
            {row.reference} — {row.status}
          </li>
        ))}
      </ul>
    </section>
  );
}
