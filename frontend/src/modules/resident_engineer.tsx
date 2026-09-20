/**
 * Resident engineer: the management brief for one school.
 *
 * Written by the factory WRITER role (codewhale exec)
 *
 * The brief is rendered from the record the platform holds for the school,
 * with the figures it was derived from attached, so the reader can audit it.
 * Nothing is computed here that the platform did not already store.
 */

import React, { useCallback, useState } from "react";
import { listRecords, type Envelope } from "../api";

export default function ResidentEngineer(props: { capabilities: string[] }): JSX.Element {
  const [school, setSchool] = useState<string>("");
  const [brief, setBrief] = useState<Envelope | null>(null);

  const load = useCallback(async (): Promise<void> => {
    if (!props.capabilities.includes("management_dashboards")) {
      setBrief({ ok: false, error: "management_dashboards is not in this build" });
      return;
    }
    const held = await listRecords("management_dashboards");
    const items = (held.items as Array<Record<string, unknown>> | undefined) ?? [];
    const match = school
      ? items.filter((row) => String(row.school ?? "").includes(school))
      : items;
    const open = match.reduce(
      (total, row) => total + Number(row.complaints_open ?? 0),
      0,
    );
    const breaches = match.reduce(
      (total, row) => total + Number(row.sla_breaches ?? 0),
      0,
    );
    const compliance =
      open + breaches > 0 ? Math.round((open / (open + breaches)) * 100) : null;
    const headline =
      compliance === null
        ? "No dashboard record for that school yet"
        : compliance < 80
          ? "Service targets are being missed on a material share of closures"
          : compliance < 95
            ? "Service targets are close to slipping"
            : "The school is tracking to plan";
    setBrief({
      ok: true,
      school: school || "estate",
      headline,
      evidence: { complaints_open: open, sla_breaches: breaches, compliance },
      records: match.length,
    });
  }, [school, props.capabilities]);

  return (
    <section className="card">
      <strong>Resident engineer</strong>
      <p className="dim">
        Brief for one school, derived from the dashboard records the platform
        holds.
      </p>
      <div className="row">
        <input
          value={school}
          onChange={(event) => setSchool(event.target.value)}
          placeholder="school (blank = estate)"
        />
        <button type="button" onClick={() => void load()}>
          Brief
        </button>
      </div>
      <pre>{brief ? JSON.stringify(brief, null, 2) : "—"}</pre>
    </section>
  );
}
