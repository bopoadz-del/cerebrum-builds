/**
 * Command center: the capability board.
 *
 * Lists every capability the platform serves, posts a record into any of them
 * against the real POST route, and re-reads the list so the operator can see
 * that the record persisted for their tenant. Nothing here is a mock: a
 * refused payload shows the platform's own error text.
 */
import { useState } from "react";
import { Capability, createRecord, listRecords } from "../api";

export interface CommandCenterProps {
  token: string;
  capabilities: Capability[];
}

export default function CommandCenter({ token, capabilities }: CommandCenterProps) {
  const [output, setOutput] = useState<Record<string, unknown> | null>(null);

  async function post(capability: Capability) {
    const sample = {
      reference: `console-${Date.now()}`,
      status: "open",
    };
    const created = await createRecord<Record<string, unknown>>(token, capability.id, sample);
    const listed = await listRecords<Record<string, unknown>>(token, capability.id);
    setOutput({ posted: created, listed: listed, entity: capability.entity });
  }

  return (
    <section style={{ marginTop: 24 }}>
      <h2 style={{ fontSize: 16 }}>Capabilities</h2>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
        {capabilities.map((capability) => (
          <div key={capability.id} style={{ border: "1px solid #8883", borderRadius: 8, padding: 12 }}>
            <h3 style={{ fontSize: 14, margin: "0 0 6px" }}>{capability.id}</h3>
            <p style={{ opacity: 0.7, fontSize: 12, margin: 0 }}>
              entity {capability.entity}
              <br />
              blocks {(capability.blocks || []).join(", ") || "—"}
            </p>
            <button onClick={() => void post(capability)}>Post a record</button>
          </div>
        ))}
      </div>
      {output && <pre style={{ maxHeight: 260, overflow: "auto" }}>{JSON.stringify(output, null, 2)}</pre>}
    </section>
  );
}
