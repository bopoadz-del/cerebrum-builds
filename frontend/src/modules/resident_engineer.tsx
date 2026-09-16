/**
 * Resident engineer: what this build is, and what it honestly is not.
 *
 * Written by the factory WRITER role (codewhale exec).
 *
 * Reads the platform's own posture: /v1/provenance, /v1/offline, /health and
 * /v1/gates. The substitutions for sealed Store modules are shown here rather
 * than hidden, because a maintenance engineer needs to know which runtime
 * module was replaced and why.
 */
import React, { useCallback, useEffect, useState } from "react";

import type { Session } from "../App";

type Posture = {
  health?: { ok?: boolean; revision?: string };
  offline?: { network?: string; sealed_vendor?: { entries?: { sealed_path: string; substituted: boolean }[] } };
  provenance?: Record<string, unknown>;
  gates?: { jobs?: unknown[] };
};

export default function ResidentEngineer(props: { session: Session }): JSX.Element {
  const { session } = props;
  const [posture, setPosture] = useState<Posture>({});
  const [error, setError] = useState("");

  const headers = { Authorization: `Bearer ${session.token}` };

  const refresh = useCallback(async () => {
    try {
      const [health, offline, provenance, gates] = await Promise.all([
        fetch("/health").then((response) => response.json()),
        fetch("/v1/offline", { headers }).then((response) => response.json()),
        fetch("/v1/provenance", { headers }).then((response) => response.json()),
        fetch("/v1/gates", { headers }).then((response) => response.json()),
      ]);
      setPosture({ health, offline, provenance, gates });
      setError("");
    } catch (exc) {
      setError(String(exc));
    }
  }, [session.token]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const entries = posture.offline?.sealed_vendor?.entries ?? [];

  return (
    <section data-module="resident_engineer">
      <h2>Resident engineer</h2>
      <button onClick={() => void refresh()}>Refresh posture</button>
      {error && <p role="alert">{error}</p>}
      <dl>
        <dt>health</dt>
        <dd>{posture.health?.ok ? `ok (revision ${posture.health?.revision ?? "unknown"})` : "not ok"}</dd>
        <dt>network</dt>
        <dd>{posture.offline?.network ?? "unknown"}</dd>
        <dt>kernel jobs</dt>
        <dd>{posture.gates?.jobs?.length ?? 0}</dd>
      </dl>
      <h3>Sealed runtime modules</h3>
      <ul>
        {entries.map((entry) => (
          <li key={entry.sealed_path}>
            {entry.sealed_path} — {entry.substituted ? "offline adapter installed" : "used as vendored"}
          </li>
        ))}
      </ul>
      <details>
        <summary>Provenance</summary>
        <pre>{JSON.stringify(posture.provenance ?? {}, null, 2)}</pre>
      </details>
    </section>
  );
}
