/**
 * FleetOps Back-Office Platform — staff console.
 *
 * Written by the factory WRITER role (codewhale exec)
 *
 * This component is the operator UI over the SAME HTTP surface the platform
 * ships: GET /v1/capabilities, POST /v1/{capability}, GET /v1/{capability},
 * GET /v1/{capability}/{id}, POST /v1/rag/ingest, POST /v1/rag/query.
 * It invents no second API and holds no domain rules of its own.
 */

import React, { useCallback, useEffect, useMemo, useState } from "react";

const TOKEN = (import.meta as any)?.env?.VITE_PLATFORM_TOKEN ?? "dev-local-token";

type Capability = {
  id: string;
  entity: string;
  http?: Record<string, string>;
};

type Row = Record<string, unknown>;

const CAPABILITIES: Capability[] = [
  { id: "fleet_registry", entity: "fleet_registry" },
  { id: "rental_contract_management", entity: "rental_contract_management" },
  { id: "maintenance_scheduling", entity: "maintenance_scheduling" },
  { id: "pricing_and_rate_cards", entity: "pricing_and_rate_cards" },
  { id: "invoicing_and_deposits", entity: "invoicing_and_deposits" },
  { id: "multi_branch_rollup", entity: "multi_branch_rollup" },
  { id: "reporting_analytics", entity: "reporting_analytics" },
  { id: "audit_trail", entity: "audit_trail" },
];

const FIELDS: Record<string, string[]> = {
  fleet_registry: ["reference", "status", "plate_number", "vin", "branch", "category", "vehicle_state", "mileage", "attachment_path"],
  rental_contract_management: ["reference", "status", "customer_name", "vehicle_reference", "branch", "pickup_date", "return_date", "extension_days", "daily_rate", "deposit_amount", "damage_notes"],
  maintenance_scheduling: ["reference", "status", "title", "vehicle_reference", "schedule_kind", "due_date", "due_mileage", "workshop", "downtime_days", "estimated_cost"],
  pricing_and_rate_cards: ["reference", "status", "category", "branch", "season", "duration_days", "base_rate", "mileage_charge", "fuel_charge", "late_return_charge", "extras_charge", "deposit_amount", "override_reason"],
  invoicing_and_deposits: ["reference", "status", "invoice_number", "contract_reference", "branch", "amount_due", "deposit_held", "credit_note", "balance_due"],
  multi_branch_rollup: ["reference", "status", "branch", "period", "fleet_utilisation", "revenue", "cost", "profit"],
  reporting_analytics: ["reference", "status", "metric", "value", "branch", "period", "query"],
  audit_trail: ["reference", "status", "action_kind", "actor", "target", "detail", "content", "attachment_path"],
};

const headers = (): Record<string, string> => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${TOKEN}`,
});

async function call(path: string, init?: RequestInit): Promise<any> {
  const response = await fetch(path, { ...init, headers: { ...headers(), ...(init?.headers ?? {}) } });
  const text = await response.text();
  const body = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(body?.detail ?? `HTTP ${response.status}`);
  }
  return body;
}

function rowsOf(body: any): Row[] {
  if (Array.isArray(body)) return body;
  for (const key of ["items", "records", "results", "rows", "data"]) {
    if (Array.isArray(body?.[key])) return body[key];
  }
  return [];
}

const App: React.FC = () => {
  const [capability, setCapability] = useState<string>(CAPABILITIES[0].id);
  const [draft, setDraft] = useState<Record<string, string>>({ status: "open", reference: "sample" });
  const [rows, setRows] = useState<Row[]>([]);
  const [notice, setNotice] = useState<string>("");
  const [question, setQuestion] = useState<string>("");
  const [hits, setHits] = useState<Row[]>([]);

  const fields = useMemo(() => FIELDS[capability] ?? ["reference", "status"], [capability]);

  const load = useCallback(async (id: string) => {
    try {
      const body = await call(`/v1/${id}`);
      setRows(rowsOf(body));
      setNotice("");
    } catch (error: any) {
      setRows([]);
      setNotice(String(error?.message ?? error));
    }
  }, []);

  useEffect(() => {
    void load(capability);
  }, [capability, load]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    try {
      const body = await call(`/v1/${capability}`, { method: "POST", body: JSON.stringify(draft) });
      setNotice(body?.ok === false ? `refused: ${body?.error}` : "created");
      await load(capability);
    } catch (error: any) {
      setNotice(String(error?.message ?? error));
    }
  };

  const ask = async () => {
    try {
      const body = await call("/v1/rag/query", { method: "POST", body: JSON.stringify({ q: question }) });
      setHits(rowsOf(body).length ? rowsOf(body) : (body?.hits ?? []));
    } catch (error: any) {
      setHits([]);
      setNotice(String(error?.message ?? error));
    }
  };

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", margin: "0 auto", maxWidth: 1080, padding: 24 }}>
      <h1>FleetOps Back-Office Platform</h1>
      <nav style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
        {CAPABILITIES.map((cap) => (
          <button
            key={cap.id}
            onClick={() => setCapability(cap.id)}
            style={{ fontWeight: cap.id === capability ? 700 : 400 }}
          >
            {cap.id.replace(/_/g, " ")}
          </button>
        ))}
      </nav>

      <form onSubmit={submit} style={{ display: "grid", gap: 8, marginBottom: 24 }}>
        <strong>{capability}</strong>
        {fields.map((field) => (
          <label key={field} style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 8 }}>
            <span>{field}</span>
            <input
              value={draft[field] ?? ""}
              onChange={(event) => setDraft({ ...draft, [field]: event.target.value })}
            />
          </label>
        ))}
        <button type="submit">POST /v1/{capability}</button>
      </form>

      {notice && <p role="status">{notice}</p>}

      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th style={{ textAlign: "left" }}>id</th>
            <th style={{ textAlign: "left" }}>reference</th>
            <th style={{ textAlign: "left" }}>status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={String(row.id ?? row.reference)}>
              <td>{String(row.id ?? "")}</td>
              <td>{String(row.reference ?? "")}</td>
              <td>{String(row.status ?? "")}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <section style={{ marginTop: 32 }}>
        <h2>Document retrieval</h2>
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="ask about a rate card, a contract or the house procedure"
          style={{ width: "70%" }}
        />
        <button onClick={ask} style={{ marginLeft: 8 }}>POST /v1/rag/query</button>
        <ul>
          {hits.map((hit, index) => (
            <li key={String(hit.id ?? index)}>
              {String(hit.text ?? hit.reference ?? JSON.stringify(hit)).slice(0, 200)}
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
};

export default App;
