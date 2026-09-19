// Command centre: the chain-wide board (sales, stock, delivery, fleet KPIs).
// Written by the factory WRITER role (codewhale exec)
import { useEffect, useState } from "react";
import { health, list, type Record } from "../api";

const PANELS = [
  "management_reporting_dashboard",
  "stock_inventory_management",
  "delivery_dispatch_tracking",
  "fleet_cost_tracking",
] as const;

export default function CommandCenter() {
  const [status, setStatus] = useState("checking");
  const [totals, setTotals] = useState<Record<string, number>>({});

  useEffect(() => {
    health()
      .then((body) => setStatus(body.status))
      .catch(() => setStatus("degraded"));
    Promise.all(PANELS.map((panel) => list(panel))).then((answers) =>
      setTotals(
        Object.fromEntries(
          PANELS.map((panel, index) => [panel, answers[index].items?.length ?? 0]),
        ),
      ),
    );
  }, []);

  return (
    <section>
      <h2>Command centre</h2>
      <p>Platform health: {status}</p>
      <ul>
        {PANELS.map((panel) => (
          <li key={panel}>
            {panel.replace(/_/g, " ")}: {totals[panel] ?? 0} record(s)
          </li>
        ))}
      </ul>
    </section>
  );
}
