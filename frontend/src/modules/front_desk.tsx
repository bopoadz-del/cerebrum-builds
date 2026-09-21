/**
 * Front desk board: arrivals, in-house guests and departures.
 *
 * Every row is a record the front desk actually posted to
 * /v1/front_desk_and_guest_stay; the board reads them back for the caller's own
 * tenant and groups them by stay status. Nothing is cached locally: a record
 * that did not persist will not appear, which is the point.
 */
import { useEffect, useState } from "react";
import { listRecords } from "../api";

interface Stay {
  id: number;
  guest_name?: string;
  room_number?: string;
  arrival_date?: string;
  departure_date?: string;
  stay_status?: string;
}

export default function FrontDeskBoard({ token }: { token: string }) {
  const [rows, setRows] = useState<Stay[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let live = true;
    void (async () => {
      const result = await listRecords<Stay>(token, "front_desk_and_guest_stay");
      if (!live) return;
      if (result.status !== 200) {
        setError(`GET /v1/front_desk_and_guest_stay answered ${result.status}`);
        return;
      }
      setRows((result.body && result.body.items) || []);
    })();
    return () => {
      live = false;
    };
  }, [token]);

  const byStatus = rows.reduce<Record<string, Stay[]>>((acc, row) => {
    const key = row.stay_status || "unknown";
    acc[key] = [...(acc[key] || []), row];
    return acc;
  }, {});

  return (
    <section>
      <h3 style={{ fontSize: 14 }}>Front desk</h3>
      {error && <p style={{ color: "#a3282f" }}>{error}</p>}
      {Object.entries(byStatus).map(([status, group]) => (
        <div key={status}>
          <strong>{status}</strong> ({group.length})
          <ul>
            {group.map((stay) => (
              <li key={stay.id}>
                room {stay.room_number} — {stay.guest_name} ({stay.arrival_date} → {stay.departure_date})
              </li>
            ))}
          </ul>
        </div>
      ))}
      {!rows.length && !error && <p>No stays recorded for this tenant yet.</p>}
    </section>
  );
}
