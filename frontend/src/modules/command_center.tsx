/**
 * Command centre: every capability the platform serves, with a live record
 * form and the records that were actually persisted.
 *
 * Written by the factory WRITER role (codewhale exec)
 */
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Capability,
  Json,
  createRecord,
  isRefusal,
  listCapabilities,
  listRecords,
  refusalReason,
} from "../api";

const SAMPLE: Record<string, Json> = {
  record_check_in: {"reference": "sample", "guest_name": "sample", "room_number": "sample", "checked_in_at": "2026-09-03T10:00:00", "guests_count": 1, "status": "open", "notes": "sample"},
  list_todays_check_ins: {"reference": "sample", "check_in_date": "2026-09-03", "room_number": "sample", "guest_name": "sample", "check_in_count": 0, "status": "open", "notes": "sample"},
};

export default function CommandCenter(): JSX.Element {
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [active, setActive] = useState<string>("");
  const [records, setRecords] = useState<Json[]>([]);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string>("");

  useEffect(() => {
    listCapabilities()
      .then((payload) => {
        setCapabilities(payload.items || []);
        if (!active && payload.items && payload.items.length) {
          setActive(payload.items[0].id);
        }
      })
      .catch((exc: Error) => setError(exc.message));
  }, [active]);

  const refresh = useCallback(async (capability: string) => {
    if (!capability) return;
    try {
      const payload = await listRecords(capability);
      setRecords(payload.items || []);
      setError("");
    } catch (exc) {
      setError((exc as Error).message);
    }
  }, []);

  useEffect(() => {
    refresh(active);
  }, [active, refresh]);

  const submit = useCallback(async () => {
    if (!active) return;
    const draft = SAMPLE[active] || { reference: "REF-1", status: "open" };
    setStatus("posting " + active);
    try {
      const body = await createRecord(active, draft);
      if (isRefusal(body)) {
        setError(refusalReason(body) || "the platform refused this record");
        setStatus("");
        return;
      }
      setStatus("stored one " + active + " record");
      setError("");
      await refresh(active);
    } catch (exc) {
      setError((exc as Error).message);
      setStatus("");
    }
  }, [active, refresh]);

  const active_capability = useMemo(
    () => capabilities.find((item) => item.id === active),
    [capabilities, active]
  );

  return (
    <section className="command-center">
      <header>
        <h1>Hotel Front Desk Log command centre</h1>
        <p>
          {capabilities.length} capabilities served by this platform. Every panel posts to the live
          route and re-reads what the platform persisted.
        </p>
      </header>
      <nav className="capability-picker">
        {capabilities.map((item) => (
          <button
            key={item.id}
            className={item.id === active ? "active" : ""}
            onClick={() => setActive(item.id)}
          >
            {item.id}
          </button>
        ))}
      </nav>
      {active_capability ? (
        <article>
          <h2>{active_capability.id}</h2>
          <code>{active_capability.http?.create}</code>
          <button onClick={submit}>Post one record</button>
          <p className="status">{status}</p>
          {error ? <p className="error">{error}</p> : null}
          <table>
            <thead>
              <tr>
                <th>id</th>
                <th>reference</th>
                <th>status</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={String(record.id)}>
                  <td>{String(record.id)}</td>
                  <td>{String(record.reference ?? "")}</td>
                  <td>{String(record.status ?? "")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      ) : null}
    </section>
  );
}
