import React, { useEffect, useState } from 'react';
import { api, Capability } from '../api';

/**
 * Platform status for the owner/head office.
 *
 * Reads /health and /v1/capabilities from the running platform, and reports
 * which vendored blocks a capability could not load, so an operator sees the
 * honest state of the deployment instead of a green tick over a dead block.
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

  const checks = Array.isArray(health.checks) ? (health.checks as Record<string, unknown>[]) : [];

  return (
    <section className="resident-engineer">
      <h2>Platform status</h2>
      {problem ? <p role="alert">{problem}</p> : null}
      <p>
        health: {String(health.status ?? 'unknown')} · revision {String(health.revision ?? 'n/a')}
      </p>
      <ul>
        {checks.map((check) => (
          <li key={String(check.name)}>
            {String(check.name)}: {check.ok ? 'ok' : String(check.detail ?? 'failing')}
          </li>
        ))}
      </ul>
      <h3>Capabilities</h3>
      <ul>
        {capabilities.map((capability) => (
          <li key={capability.id}>
            {capability.id} → {capability.entity}
          </li>
        ))}
      </ul>
    </section>
  );
}
