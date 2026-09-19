import React, { useEffect, useState } from 'react';
import { api, Capability, PlatformRecord } from '../api';

/**
 * Branch and consolidated command centre.
 *
 * Lists every capability the booted backend publishes, then reads and writes
 * through the live routes: a capability is only shown when GET returns records
 * the platform actually stored. No sample rows are invented in the client.
 */
export default function CommandCenter({ capabilities }: { capabilities: Capability[] }) {
  const [selected, setSelected] = useState<string>('');
  const [records, setRecords] = useState<PlatformRecord[]>([]);
  const [status, setStatus] = useState<string>('');

  const active = selected || capabilities[0]?.id || '';

  useEffect(() => {
    if (!active) return;
    api
      .list(active)
      .then((payload) => {
        setRecords(payload.items || []);
        setStatus(`${payload.total ?? (payload.items || []).length} record(s) in ${active}`);
      })
      .catch((exc: Error) => setStatus(exc.message));
  }, [active]);

  return (
    <section className="command-center">
      <h2>Per-branch and consolidated operations</h2>
      <select value={active} onChange={(event) => setSelected(event.target.value)}>
        {capabilities.map((capability) => (
          <option key={capability.id} value={capability.id}>
            {capability.id}
          </option>
        ))}
      </select>
      <p>{status}</p>
      <table>
        <thead>
          <tr>
            <th>id</th>
            <th>reference</th>
            <th>branch</th>
            <th>status</th>
          </tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr key={String(record.id)}>
              <td>{String(record.id)}</td>
              <td>{String(record.reference ?? '')}</td>
              <td>{String(record.branch ?? '')}</td>
              <td>{String(record.status ?? '')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
