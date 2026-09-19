// Resident engineer: what the platform can honestly claim right now.
// Written by the factory WRITER role (codewhale exec)
import { useEffect, useState } from "react";
import { getJobs, getGates, type Job } from "../api";

export default function ResidentEngineer() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [coverage, setCoverage] = useState<string[]>([]);

  useEffect(() => {
    getJobs().then((body) => setJobs(body.jobs ?? [])).catch(() => setJobs([]));
    getGates()
      .then((body) => setCoverage((body.suite ?? []).map((item) => item.file)))
      .catch(() => setCoverage([]));
  }, []);

  return (
    <section>
      <h2>Resident engineer</h2>
      <p>Kernel jobs and the suite that judges this build.</p>
      <ul>
        {jobs.map((job) => (
          <li key={job.kernel}>
            {job.kernel} — {job.title} ({job.agent})
          </li>
        ))}
      </ul>
      <ul>
        {coverage.map((file) => (
          <li key={file}>{file}</li>
        ))}
      </ul>
    </section>
  );
}
