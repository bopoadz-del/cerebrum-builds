import React, { useEffect, useState } from 'react';
import { api, Capability } from '../api';

/**
 * Platform status for the finance controllers.
 *
 * Reads /health and /v1/capabilities from the running platform and reports the
 * capability surface it actually serves. The integration placeholders (Google
 * Drive, Sage) are listed as not production-cleared; the platform does not
 * claim a connector it does not have.
 */
export default function ResidentEngineer({ capabilities }: { capabilities: Capability[] }) {
  const [health, setHealth] = useState<Record<string, unknown>>({});
  const [problem, setProblem] = useState<string>('');

  useEffect(() => {
    api
      .health()
      .then((payload) => setHealth(payload))
      .catch((exc: Error) => setProblem(exc.message));
  }, []);

  const checks = Array.isArray(health.checks)
    ? (health.checks as { name: string; ok: boolean; detail?: string }[])
    : [];

  return (
    <section className="platform-status">
      <h2>Platform status</h2>
      {problem ? <p role="alert">{problem}</p> : null}
      <p>
        status: {String(health.status ?? 'unknown')} · version:{' '}
        {String(health.revision ?? health.version ?? 'n/a')}
      </p>
      <ul>
        {checks.map((check) => (
          <li key={check.name}>
            {check.ok ? 'ok' : 'FAILED'} — {check.name}
            {check.detail ? `: ${check.detail}` : ''}
          </li>
        ))}
      </ul>
      <h3>Served capabilities</h3>
      <ul>
        {capabilities.map((capability) => (
          <li key={capability.id}>
            {capability.id} → {capability.http.create} · {capability.http.list}
          </li>
        ))}
      </ul>
    </section>
  );
}
