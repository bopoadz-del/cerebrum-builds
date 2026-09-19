// Document Q&A — Ingests uploaded unit price lists and procedures and answers operational questions over them.
// Written by the factory WRITER role (codewhale exec)
import { useState } from "react";
import { create, list, type CapabilityId, type Record } from "../api";

export default function DocumentKnowledgeQa({ capability }: { capability: CapabilityId }) {
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
      document_title: secondary,
      question: secondary,
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
      <h2>Document Q&A</h2>
      <p>Ingests uploaded unit price lists and procedures and answers operational questions over them.</p>
      <label>
        document_title
        <input value={primary} onChange={(event) => setPrimary(event.target.value)} />
      </label>
      <label>
        question
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
