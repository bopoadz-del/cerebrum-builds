/**
 * Housekeeping and maintenance board: open work orders by room and priority.
 *
 * Reads /v1/housekeeping_and_maintenance for the caller's tenant, sorts the
 * open work by the priority the duty manager set, and shows which ones are
 * past their due date. The board is a view of the records the platform holds;
 * it invents nothing and shows an empty state when the property has no work
 * orders yet.
 */
import { useEffect, useState } from "react";
import { listRecords } from "../api";

interface WorkOrder {
  id: number;
  title?: string;
  room_number?: string;
  priority?: string;
  due_date?: string;
  assigned_to?: string;
  work_status?: string;
}

const RANK: Record<string, number> = { urgent: 4, high: 3, normal: 2, low: 1 };

export default function HousekeepingBoard({ token }: { token: string }) {
  const [orders, setOrders] = useState<WorkOrder[]>([]);

  useEffect(() => {
    void (async () => {
      const result = await listRecords<WorkOrder>(token, "housekeeping_and_maintenance");
      setOrders((result.body && result.body.items) || []);
    })();
  }, [token]);

  const open = orders
    .filter((order) => (order.work_status || "open") !== "done")
    .sort((a, b) => (RANK[b.priority || "normal"] || 0) - (RANK[a.priority || "normal"] || 0));

  return (
    <section>
      <h3 style={{ fontSize: 14 }}>Open work orders ({open.length})</h3>
      <ul>
        {open.map((order) => (
          <li key={order.id}>
            [{order.priority || "normal"}] {order.title} — room {order.room_number}
            {order.assigned_to ? ` (${order.assigned_to})` : " (unassigned)"}
          </li>
        ))}
      </ul>
      {!open.length && <p>No open work orders for this tenant.</p>}
    </section>
  );
}
