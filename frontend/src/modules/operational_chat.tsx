/**
 * Operational chat: type what you did, the panel routes it to the capability
 * that owns it and posts the record you confirm.
 *
 * Written by the factory WRITER role (codewhale exec)
 *
 * The routing is deterministic keyword triage over the capability roster --
 * there is no cloud LLM in this platform (P1), and the panel says so instead
 * of pretending to answer questions it cannot ground. Answers come back from
 * the capability's own handler result, not from a local guess.
 */
import React, { useCallback, useMemo, useState } from "react";
import { Json, createRecord, isRefusal, refusalReason } from "../api";

const ROUTES: Array<{ capability: string; keywords: string[] }> = [
  { capability: "record_guest_check_in", keywords: ["check in", "check-in", "checked in", "arrived", "guest", "room"] },
  { capability: "list_todays_check_ins", keywords: ["today", "arrivals", "list", "who is in", "in house", "board"] },
];

export function routePrompt(prompt: string): string {
  const text = prompt.toLowerCase();
  for (const route of ROUTES) {
    if (route.keywords.some((keyword) => text.includes(keyword))) {
      return route.capability;
    }
  }
  return "record_guest_check_in";
}

export default function OperationalChat(): JSX.Element {
  const [prompt, setPrompt] = useState<string>("");
  const [answer, setAnswer] = useState<Json | null>(null);
  const [error, setError] = useState<string>("");

  const target = useMemo(() => routePrompt(prompt), [prompt]);

  const send = useCallback(async () => {
    const text = prompt.trim();
    if (!text) return;
    setError("");
    setAnswer(null);
    const capability = routePrompt(text);
    const record: Json = {
      reference: `CHAT-${Date.now().toString(36)}`,
      status: "open",
      notes: text,
    };
    if (capability === "record_guest_check_in") {
      record.guest_name = (text.match(/guest ([\w' -]{1,60})/i) || [null, text.slice(0, 60)])[1];
      record.room_number = (text.match(/room ([A-Za-z0-9-]{1,10})/i) || [null, "unassigned"])[1];
      record.checked_in_at = new Date().toISOString();
    }
    if (capability === "list_todays_check_ins") {
      record.check_in_date = new Date().toISOString().slice(0, 10);
      record.room_number = (text.match(/room ([A-Za-z0-9-]{1,10})/i) || [null, "front desk"])[1];
      record.guest_name = (text.match(/guest ([\w' -]{1,60})/i) || [null, "front desk"])[1];
      record.check_in_count = 0;
    }
    try {
      const body = await createRecord(capability, record);
      if (isRefusal(body)) {
        setError(refusalReason(body) || "the platform refused this record");
        return;
      }
      setAnswer(body);
    } catch (exc) {
      setError((exc as Error).message);
    }
  }, [prompt]);

  return (
    <section className="operational-chat">
      <h2>Operational chat</h2>
      <p>
        Deterministic triage: your note is filed against the capability that owns it. No outbound
        model is called -- this platform runs offline (P1).
      </p>
      <textarea
        value={prompt}
        rows={4}
        placeholder="Irrigated the north block for four hours with the pivot"
        onChange={(event) => setPrompt(event.target.value)}
      />
      <p>
        routes to <strong>{target}</strong>
      </p>
      <button onClick={send}>File it</button>
      {error ? <p className="error">{error}</p> : null}
      {answer ? <pre>{JSON.stringify(answer, null, 2).slice(0, 4000)}</pre> : null}
    </section>
  );
}
