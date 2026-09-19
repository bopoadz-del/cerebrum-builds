// Audit trail — Keeps an auditable trail of stock, delivery, upload and acknowledgment events with hashes.
// Written by the factory WRITER role (codewhale exec)
import { useState } from "react";
import { create, list, type CapabilityId, type Record } from "../api";

export default function AuditEvidenceTrail({ capability }: { capability: CapabilityId }) {
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
      event_type: secondary,
      actor: secondary,
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
      <h2>Audit trail</h2>
      <p>Keeps an auditable trail of stock, delivery, upload and acknowledgment events with hashes.</p>
      <label>
        event_type
        <input value={primary} onChange={(event) => setPrimary(event.target.value)} />
      </label>
      <label>
        actor
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
