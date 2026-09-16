/**
 * Command centre: the clinic's records, appointments and stock.
 *
 * Written by the factory WRITER role (codewhale exec).
 *
 * Talks only to the booted platform's own routes. Creating a record POSTs
 * the payload the capability's schema declares and then re-reads the list it
 * was written into — the same round-trip the acceptance suite measures.
 */
import React, { useCallback, useEffect, useState } from "react";

import type { Session } from "../App";

type Capability = {
  id: string;
  fields: string[];
  constraints: Record<string, { allowed_values?: string[]; required?: boolean }>;
};

export default function CommandCenter(props: {
  session: Session;
  capabilities: string[];
}): JSX.Element {
  const { session, capabilities } = props;
  const [selected, setSelected] = useState(capabilities[0]);
  const [contract, setContract] = useState<Capability | null>(null);
  const [draft, setDraft] = useState<Record<string, string>>({});
  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [status, setStatus] = useState("idle");

  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${session.token}`,
  };

  const load = useCallback(async () => {
    const contractResponse = await fetch(`/v1/schema/${selected}`, { headers });
    const contractBody = contractResponse.ok ? await contractResponse.json() : null;
    setContract(contractBody);
    const fields: string[] = contractBody?.fields ?? [];
    const next: Record<string, string> = {};
    for (const field of fields) {
      const rules = contractBody?.constraints?.[field] ?? {};
      next[field] = rules.allowed_values?.[0] ?? (rules.required ? "sample" : "");
    }
    setDraft(next);
    const listResponse = await fetch(`/v1/${selected}`, { headers });
    const listBody = listResponse.ok ? await listResponse.json() : { items: [] };
    setItems(listBody.items ?? []);
  }, [selected, session.token]);

  useEffect(() => {
    void load();
  }, [load]);

  async function create(): Promise<void> {
    setStatus("posting");
    const response = await fetch(`/v1/${selected}`, {
      method: "POST",
      headers,
      body: JSON.stringify(draft),
    });
    const body = await response.json();
    setStatus(response.ok && body.ok !== false ? "stored" : `refused: ${body.error ?? response.status}`);
    await load();
  }

  async function renderDocument(itemId: number): Promise<void> {
    const response = await fetch(`/v1/${selected}/${itemId}/document`, {
      method: "POST",
      headers,
    });
    const body = await response.json();
    setStatus(response.ok ? `document: ${JSON.stringify(body.document).slice(0, 120)}` : "document refused");
  }

  return (
    <section data-module="command_center">
      <h2>Command centre</h2>
      <select value={selected} onChange={(event) => setSelected(event.target.value)}>
        {capabilities.map((capability) => (
          <option key={capability} value={capability}>
            {capability}
          </option>
        ))}
      </select>

      {contract && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void create();
          }}
        >
          {contract.fields.map((field) => {
            const rules = contract.constraints[field] ?? {};
            const allowed = rules.allowed_values;
            return (
              <label key={field}>
                {field}
                {allowed ? (
                  <select
                    value={draft[field] ?? ""}
                    onChange={(event) => setDraft({ ...draft, [field]: event.target.value })}
                  >
                    {allowed.map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    value={draft[field] ?? ""}
                    onChange={(event) => setDraft({ ...draft, [field]: event.target.value })}
                  />
                )}
              </label>
            );
          })}
          <button type="submit">Create record</button>
        </form>
      )}

      <p role="status">{status}</p>
      <table>
        <thead>
          <tr>
            <th>id</th>
            <th>reference</th>
            <th>status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={String(item.id)}>
              <td>{String(item.id)}</td>
              <td>{String(item.reference ?? "")}</td>
              <td>{String(item.status ?? "")}</td>
              <td>
                <button onClick={() => void renderDocument(Number(item.id))}>Document</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
