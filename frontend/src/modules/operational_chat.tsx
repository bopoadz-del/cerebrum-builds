/* Operational chat: front-desk intake against the live capability routes.
 *
 * The front desk types a line per field; the module POSTs it to
 * /v1/<capability_id> and shows exactly what the backend stored. This is the
 * same POST/GET contract the pilot suite exercises — no second API.
 */

import { useMemo, useState } from "react";

import { authHeaders, type Capability } from "../App";

interface Props {
  capabilities: Capability[];
}

const INTAKE_ORDER = [
  "patient_and_owner_records",
  "appointment_scheduling",
  "clinical_visit_notes_and_treatment_plans",
  "client_communication_and_reminders",
];

export default function OperationalChatModule({ capabilities }: Props) {
  const choices = useMemo(() => {
    if (!capabilities.length) return INTAKE_ORDER;
    return capabilities.map((cap) => cap.id);
  }, [capabilities]);
  const [capability, setCapability] = useState(choices[0] ?? "");
  const [line, setLine] = useState("");
  const [log, setLog] = useState<string[]>([]);

  const submit = async () => {
    if (!capability || !line.trim()) return;
    const payload: Record<string, unknown> = {
      reference: `chat-${Date.now()}`,
      status: "open",
      owner_name: "front desk intake",
      patient_name: line.trim(),
      reminder_type: "follow_up",
    };
    const resp = await fetch(`/v1/${capability}`, {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify(payload),
    });
    const body = await resp.json().catch(() => ({}));
    const verdict =
      resp.ok && body?.ok !== false
        ? `stored id=${body?.stored?.id ?? "?"}`
        : `refused: ${body?.error || body?.detail || resp.status}`;
    setLog((prev) => [`${capability}: ${line.trim()} → ${verdict}`, ...prev].slice(0, 20));
    setLine("");
  };

  return (
    <section data-module="operational_chat">
      <h2>Front-desk intake</h2>
      <label>
        Capability
        <select value={capability} onChange={(event) => setCapability(event.target.value)}>
          {choices.map((id) => (
            <option key={id} value={id}>
              {id.replace(/_/g, " ")}
            </option>
          ))}
        </select>
      </label>
      <label>
        Patient or task
        <input
          value={line}
          onChange={(event) => setLine(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") void submit();
          }}
        />
      </label>
      <button onClick={() => void submit()}>Record</button>
      <ul>
        {log.map((entry) => (
          <li key={entry}>{entry}</li>
        ))}
      </ul>
    </section>
  );
}
