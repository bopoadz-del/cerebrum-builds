// Procedures, readiness and audit — Per-shop and per-run checklists, readiness before service, and the immutable evidence trail of checks.
// Written by the factory WRITER role (codewhale exec)
import { useState } from "react";
import { create, list, type CapabilityId, type Record } from "../api";

export default function ProceduresReadinessAndAuditTrail({ capability }: { capability: CapabilityId }) {
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
      procedure_code: secondary,
      procedure_title: secondary,
      shop_code: "shop-1",
      checklist: "oven_on,chiller_ok",
      due_date: "2026-09-03",
      actor: "manager-1",
      event_type: "procedure_check",

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
      <h2>Procedures, readiness and audit</h2>
      <p>Per-shop and per-run checklists, readiness before service, and the immutable evidence trail of checks.</p>
      <label>
        procedure_code
        <input value={primary} onChange={(event) => setPrimary(event.target.value)} />
      </label>
      <label>
        procedure_title
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
