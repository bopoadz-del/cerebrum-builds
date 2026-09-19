/* Command center: practice-wide operational board.
 *
 * Reads /v1/capabilities to learn the live surface and /v1/<capability> to
 * render the records this practice actually holds. Owner-facing only.
 */

import { useMemo, useState } from "react";

import { authHeaders, type Capability } from "../App";

interface Props {
  capabilities: Capability[];
}

const PRIORITY = [
  "appointment_scheduling",
  "vaccination_tracking",
  "patient_and_owner_records",
  "billing_and_invoicing",
];

export default function CommandCenterModule({ capabilities }: Props) {
  const ordered = useMemo(() => {
    const rank = (id: string) => {
      const idx = PRIORITY.indexOf(id);
      return idx === -1 ? PRIORITY.length : idx;
    };
    return [...capabilities].sort((a, b) => rank(a.id) - rank(b.id));
  }, [capabilities]);
  const [selected, setSelected] = useState("");
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [status, setStatus] = useState("select a capability");

  const load = async (id: string) => {
    setSelected(id);
    setStatus("loading");
    try {
      const resp = await fetch(`/v1/${id}?limit=10`, { headers: authHeaders() });
      const body = await resp.json();
      const items = (body?.items as Record<string, unknown>[]) || [];
      setRows(items);
      setStatus(items.length ? `${items.length} record(s)` : "no records yet");
    } catch (exc) {
      setRows([]);
      setStatus(`error: ${String(exc)}`);
    }
  };

  return (
    <section data-module="command_center">
      <h2>Practice command center</h2>
      <ul>
        {ordered.map((cap) => (
          <li key={cap.id}>
            <button onClick={() => load(cap.id)} aria-pressed={selected === cap.id}>
              {cap.id.replace(/_/g, " ")}
            </button>
            <code>{cap.entity}</code>
          </li>
        ))}
      </ul>
      <p>{status}</p>
      <table>
        <tbody>
          {rows.map((row, index) => (
            <tr key={String(row.id ?? index)}>
              {Object.entries(row)
                .slice(0, 5)
                .map(([key, value]) => (
                  <td key={key}>{String(value ?? "")}</td>
                ))}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
