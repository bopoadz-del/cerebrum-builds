import { useEffect, useMemo, useState } from "react";

import {
  BoardRow,
  CheckIn,
  TOKEN_STORAGE_KEY,
  checkArrivals,
  listCheckins,
  recordCheckIn,
  setToken,
  token,
  vendorHealth,
} from "./api";
import CommandCenter from "./modules/command_center";
import Knowledge from "./modules/knowledge";
import OperationalChat from "./modules/operational_chat";
import ResidentEngineer from "./modules/resident_engineer";

type Tab = "arrivals" | "checkin" | "knowledge" | "modules";

export default function App() {
  const [tab, setTab] = useState<Tab>("arrivals");
  const [rows, setRows] = useState<BoardRow[]>([]);
  const [checkins, setCheckins] = useState<CheckIn[]>([]);
  const [error, setError] = useState<string>("");
  const [health, setHealth] = useState<{ ok: boolean; unavailable: string[] } | null>(null);
  const [form, setForm] = useState({
    reference: "FD-1",
    guest_name: "",
    room_number: "",
    nights: 1,
    arrival_time: "15:00:00",
    status: "open",
    notes: "",
  });

  const load = useMemo(
    () => async () => {
      try {
        setError("");
        const [board, log, status] = await Promise.all([
          checkArrivals(),
          listCheckins(),
          vendorHealth(),
        ]);
        setRows(board.items || []);
        setCheckins(log.items || []);
        setHealth(status);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      }
    },
    [],
  );

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    try {
      setError("");
      await recordCheckIn(form);
      setForm({ ...form, guest_name: "", room_number: "", notes: "" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <main className="desk">
      <header>
        <h1>Boutique Front Desk</h1>
        <p>40 rooms. One arrival board. No paper log.</p>
        <label>
          Platform token
          <input
            defaultValue={token()}
            onChange={(event) => {
              setToken(event.target.value);
            }}
          />
        </label>
        <nav>
          <button onClick={() => setTab("arrivals")}>Arrivals</button>
          <button onClick={() => setTab("checkin")}>New check-in</button>
          <button onClick={() => setTab("knowledge")}>House knowledge</button>
          <button onClick={() => setTab("modules")}>Operations</button>
        </nav>
      </header>

      {error ? <p className="error">{error}</p> : null}
      {health && !health.ok ? (
        <p className="warn">
          Blocks unavailable: {health.unavailable.join(", ")} (named in /v1/vendor_health)
        </p>
      ) : null}

      {tab === "arrivals" ? (
        <section>
          <h2>Today's arrivals</h2>
          <table>
            <thead>
              <tr>
                <th>Guest</th>
                <th>Room</th>
                <th>Date</th>
                <th>Arrived</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>{row.guest_name}</td>
                  <td>{row.room_number}</td>
                  <td>{row.arrival_date}</td>
                  <td>{row.arrived ? "arrived" : "expected"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}

      {tab === "checkin" ? (
        <section>
          <h2>Record a check-in</h2>
          <form onSubmit={submit}>
            <input
              placeholder="guest name"
              value={form.guest_name}
              onChange={(event) => setForm({ ...form, guest_name: event.target.value })}
            />
            <input
              placeholder="room"
              value={form.room_number}
              onChange={(event) => setForm({ ...form, room_number: event.target.value })}
            />
            <input
              type="number"
              min={1}
              value={form.nights}
              onChange={(event) => setForm({ ...form, nights: Number(event.target.value) })}
            />
            <input
              placeholder="arrival HH:MM:SS"
              value={form.arrival_time}
              onChange={(event) => setForm({ ...form, arrival_time: event.target.value })}
            />
            <button type="submit">Record check-in</button>
          </form>
          <ul>
            {checkins.map((row) => (
              <li key={row.id}>
                {row.guest_name} · room {row.room_number} · {row.nights} night(s) ·{" "}
                {row.arrival_time}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {tab === "knowledge" ? (
        <section className="knowledge-panel">
          <Knowledge />
        </section>
      ) : null}

      {tab === "modules" ? (
        <section className="modules">
          <CommandCenter />
          <OperationalChat />
          <ResidentEngineer />
        </section>
      ) : null}
    </main>
  );
}
