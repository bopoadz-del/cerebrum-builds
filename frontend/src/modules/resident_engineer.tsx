/* Resident engineer: runtime truth for the practice operator.
 *
 * Reads the fail-closed health contract, the kernel job roster and the
 * capability manifest. If the practice is degraded the operator sees which
 * check failed instead of a green badge that means nothing.
 */

import { useEffect, useState } from "react";

import { authHeaders } from "../App";

interface Check {
  name: string;
  ok: boolean;
  detail?: string;
}

export default function ResidentEngineerModule() {
  const [health, setHealth] = useState<{ status?: string; ok?: boolean; checks?: Check[] }>({});
  const [jobs, setJobs] = useState<{ kernel: string; title: string; mandate: string }[]>([]);
  const [revision, setRevision] = useState("");

  useEffect(() => {
    fetch("/health")
      .then((r) => r.json())
      .then(setHealth)
      .catch(() => setHealth({ status: "unreachable", ok: false }));
    fetch("/v1/jobs", { headers: authHeaders() })
      .then((r) => r.json())
      .then((body) => setJobs(body?.jobs || []))
      .catch(() => setJobs([]));
    fetch("/v1/provenance", { headers: authHeaders() })
      .then((r) => r.json())
      .then((body) => setRevision(String(body?.build?.engine || "unknown engine")))
      .catch(() => setRevision("unknown"));
  }, []);

  return (
    <section data-module="resident_engineer">
      <h2>Runtime truth</h2>
      <p>
        health: <strong>{health.status || "unknown"}</strong> (ok={String(health.ok)})
      </p>
      <p>build engine: {revision}</p>
      <ul>
        {(health.checks || []).map((check) => (
          <li key={check.name} data-ok={String(check.ok)}>
            {check.name}: {check.ok ? "ok" : check.detail || "failed"}
          </li>
        ))}
      </ul>
      <h3>Kernel roster</h3>
      <ul>
        {jobs.map((job) => (
          <li key={job.kernel}>
            <strong>{job.kernel}</strong> — {job.title}
          </li>
        ))}
      </ul>
    </section>
  );
}
