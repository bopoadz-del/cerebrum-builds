// Workforce — Administers users, roles, shop assignments and driver shifts.
// Written by the factory WRITER role (codewhale exec)
import { useState } from "react";
import { create, list, type CapabilityId, type Record } from "../api";

export default function UserRolesWorkforce({ capability }: { capability: CapabilityId }) {
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
      user_name: secondary,
      role: secondary,
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
      <h2>Workforce</h2>
      <p>Administers users, roles, shop assignments and driver shifts.</p>
      <label>
        user_name
        <input value={primary} onChange={(event) => setPrimary(event.target.value)} />
      </label>
      <label>
        role
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
