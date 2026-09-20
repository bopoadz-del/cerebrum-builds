/**
 * Command centre: complaints and teams, driven from the live routes.
 *
 * Written by the factory WRITER role (codewhale exec)
 *
 * Management logs a complaint on a parent's or a school's behalf, and sees
 * the complaints the platform already holds. Every write goes through
 * POST /v1/complaints_management and every read through GET on the same
 * capability, so this screen cannot show a record the platform did not store.
 */

import React, { useCallback, useEffect, useState } from "react";
import { createRecord, listRecords, type Envelope } from "../api";

const CATEGORIES = [
  "electrical",
  "plumbing",
  "hvac",
  "cleaning",
  "safety",
  "grounds",
  "furniture",
  "it_av",
  "pest_control",
  "other",
];

const PRIORITIES = ["critical", "high", "medium", "low"];

const SCHOOLS = [
  "al-barsha-primary",
  "al-quoz-secondary",
  "deira-primary",
  "jumeirah-primary",
  "karama-secondary",
  "mirdif-primary",
  "nad-al-shema-secondary",
  "silicon-oasis-primary",
  "the-gardens-primary",
  "warqa-secondary",
];

export default function CommandCenter(props: { capabilities: string[] }): JSX.Element {
  const holds = props.capabilities.includes("complaints_management");
  const [school, setSchool] = useState<string>(SCHOOLS[0]);
  const [category, setCategory] = useState<string>(CATEGORIES[3]);
  const [priority, setPriority] = useState<string>(PRIORITIES[1]);
  const [description, setDescription] = useState<string>("");
  const [raisedBy, setRaisedBy] = useState<string>("");
  const [log, setLog] = useState<Envelope | null>(null);

  const refresh = useCallback(async (): Promise<void> => {
    if (!holds) return;
    setLog(await listRecords("complaints_management"));
  }, [holds]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const submit = useCallback(async (): Promise<void> => {
    if (!holds) return;
    const record = {
      reference: `CMP-${Date.now()}`,
      status: "open",
      school,
      category,
      priority,
      description: description || `${category} issue reported at ${school}`,
      raised_by: raisedBy || "management",
      raised_by_role: "management",
    };
    const answer = await createRecord("complaints_management", record);
    setLog(answer);
    await refresh();
  }, [holds, school, category, priority, description, raisedBy, refresh]);

  if (!holds) {
    return (
      <section className="card">
        <strong>Command centre</strong>
        <p className="dim">This build does not declare complaints_management.</p>
      </section>
    );
  }

  return (
    <section className="card">
      <strong>Log a complaint</strong>
      <p className="dim">
        Management may enter a complaint on a school&apos;s or a parent&apos;s
        behalf; the platform computes the service target and routes it.
      </p>
      <div className="row">
        <select value={school} onChange={(e) => setSchool(e.target.value)}>
          {SCHOOLS.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          {CATEGORIES.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        <select value={priority} onChange={(e) => setPriority(e.target.value)}>
          {PRIORITIES.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
        <input
          value={raisedBy}
          onChange={(e) => setRaisedBy(e.target.value)}
          placeholder="raised by"
        />
      </div>
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        placeholder="what is wrong"
        rows={3}
      />
      <div className="row">
        <button type="button" onClick={() => void submit()}>
          Create
        </button>
        <button type="button" onClick={() => void refresh()}>
          List
        </button>
      </div>
      <pre>{log ? JSON.stringify(log, null, 2) : "—"}</pre>
    </section>
  );
}
