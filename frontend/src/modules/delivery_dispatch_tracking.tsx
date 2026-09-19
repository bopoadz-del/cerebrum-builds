// Delivery dispatch — Assigns the ~30 daily deliveries to drivers and the 12 bikes and cars, and tracks status and exceptions.
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
      shop_code: "shop-1",
      driver_code: "driver-1",
      vehicle_code: "bike-1",
      vehicle_type: "bike",
      delivery_address: secondary,
      scheduled_at: "2026-09-03T10:00:00",
      delivery_state: "pending",

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
      <h2>Delivery dispatch</h2>
      <p>Assigns the ~30 daily deliveries to drivers and the 12 bikes and cars, and tracks status and exceptions.</p>
      <label>
        order_code
        <input value={primary} onChange={(event) => setPrimary(event.target.value)} />
      </label>
      <label>
        delivery_address
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
