import { useEffect, useState } from "react";
import { Api, type Authority } from "../api";
import { layerBadge } from "../App";

type Diagnostic = { label: string; value: string; authority?: Authority };

export function ResidentEngineer(props: { api: Api }) {
  const { api } = props;
  const [rows, setRows] = useState<Diagnostic[]>([]);

  useEffect(() => {
    const load = async () => {
      const connectors = await api.connectors_();
      const list = (connectors.payload.connectors ?? []) as {
        connector: string;
        mode: string;
        blocks_unavailable: string[];
      }[];
      setRows(
        list.map((row) => ({
          label: row.connector,
          value:
            row.mode +
            (row.blocks_unavailable.length ? ` — missing ${row.blocks_unavailable.join(", ")}` : ""),
          authority: connectors.payload.authority,
        })),
      );
    };
    void load();
  }, [api]);

  return (
    <section className="card">
      <h2>Resident engineer — what is connected, what is stubbed</h2>
      <table>
        <thead>
          <tr>
            <th>Connector</th>
            <th>State</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <td>{row.label}</td>
              <td>
                {row.value}
                {layerBadge(row.authority)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="dim">
        A stub declares the setting it is missing; it never reports a delivery it did not make.
      </div>
    </section>
  );
}
