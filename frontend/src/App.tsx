/**
 * CallOps operator console — React source.
 *
 * The same operations desk as the served artifact (app/static/index.html),
 * as components: a bearer-token field, a capability picker populated from
 * GET /v1/capabilities, a form generated from the capability's declared
 * fields, a Send that POSTs the payload to POST /v1/<capability>, a response
 * panel that renders ok / error / result plus the authority layer the answer
 * carries (precedence.v1: certified > documents > formulas > procedures), and
 * a recent-records list that re-reads GET /v1/<capability> after a write so
 * the persisted row is visible.
 *
 * This tree is reference source only: the artifact the platform serves at
 * GET / is app/static/index.html, which needs no build step. It therefore
 * has no dependency beyond react itself and calls the platform's own routes
 * directly — there is no client-side mock and no second backend.
 */
import { useCallback, useEffect, useMemo, useState } from "react";

/** precedence.v1 — the authority ladder every retrieved answer carries. */
export const AUTHORITY_LADDER = ["certified", "documents", "formulas", "procedures"] as const;

export type AuthorityLabel = (typeof AUTHORITY_LADDER)[number];

export interface CapabilityInfo {
  id: string;
  entity?: string;
  source?: string;
  blocks?: string[];
  http?: Record<string, string>;
}

export interface FieldSpec {
  name: string;
  label: string;
  kind: "text" | "number" | "select" | "textarea" | "bool";
  options?: string[];
  value?: string | number | boolean;
  required?: boolean;
  min?: number;
  max?: number;
}

export interface CapabilitySpec {
  summary: string;
  fields: FieldSpec[];
}

export interface ApiResult<T> {
  status: number;
  body: T | null;
}

interface Envelope {
  ok?: boolean;
  capability?: string;
  error?: unknown;
  result?: Record<string, unknown>;
  stored?: Record<string, unknown>;
  items?: Array<Record<string, unknown>>;
  total?: number;
  authority_label?: string;
}

const STATUS: FieldSpec = {
  name: "status",
  label: "status",
  kind: "select",
  options: ["open", "in_progress", "closed"],
  value: "open",
  required: true,
};

const AUTHORITY_FIELD: FieldSpec = {
  name: "authority_label",
  label: "authority_label",
  kind: "select",
  options: [...AUTHORITY_LADDER],
  value: "certified",
};

const NOTES: FieldSpec = { name: "notes", label: "notes", kind: "textarea", value: "" };

const CALL_SID: FieldSpec = {
  name: "call_sid",
  label: "call_sid",
  kind: "text",
  value: "CA1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d",
  required: true,
};

const OUTCOME: FieldSpec = {
  name: "outcome",
  label: "outcome",
  kind: "select",
  options: ["project_interested", "other_re_interested", "not_interested"],
  value: "project_interested",
  required: true,
};

/**
 * Field lists per capability, from the server-side contract (app/models.py
 * plus each route's edge guard). This is the whole "form generator" input:
 * the desk renders exactly these fields and posts exactly these value
 * vocabularies, so a Send is a record the API accepts.
 */
export const CAPABILITY_FIELDS: Record<string, CapabilitySpec> = {
  lead_intake_and_dial_queue: {
    summary:
      "Capture an inbound lead file and place it on the dial queue (language, project, call cap, concurrency).",
    fields: [
      { name: "reference", label: "reference", kind: "text", value: "LEAD-1001", required: true },
      STATUS,
      { name: "lead_name", label: "lead_name", kind: "text", value: "Noura Al-Farsi", required: true },
      { name: "phone", label: "phone (E.164)", kind: "text", value: "+971500001001", required: true },
      { name: "language", label: "language", kind: "select", options: ["en", "ar"], value: "en", required: true },
      { name: "project_tag", label: "project_tag", kind: "text", value: "PSI-MARINA", required: true },
      { name: "daily_call_cap", label: "daily_call_cap", kind: "number", value: 40, min: 1, max: 100000 },
      { name: "concurrency", label: "concurrency", kind: "number", value: 2, min: 1, max: 50 },
      { name: "attempt_count", label: "attempt_count", kind: "number", value: 0, min: 0, max: 3 },
      { name: "retry_backoff_minutes", label: "retry_backoff_minutes", kind: "number", value: 15, min: 0, max: 1440 },
      {
        name: "queue_status",
        label: "queue_status",
        kind: "select",
        options: ["queued", "dialing", "paused", "exhausted"],
        value: "queued",
      },
      NOTES,
    ],
  },
  call_state_machine: {
    summary:
      "One call's lifecycle keyed to its Call SID: queued -> dialing -> answered -> pitched -> qualified -> transferred | callback | closed, with the call window as a guard.",
    fields: [
      { name: "reference", label: "reference", kind: "text", value: "CALL-1001", required: true },
      STATUS,
      CALL_SID,
      {
        name: "current_state",
        label: "current_state",
        kind: "select",
        options: ["queued", "dialing", "answered", "pitched", "qualified", "transferred", "callback", "closed"],
        value: "queued",
        required: true,
      },
      {
        name: "previous_state",
        label: "previous_state",
        kind: "select",
        options: ["queued", "dialing", "answered", "pitched", "qualified", "transferred", "callback", "closed"],
        value: "queued",
      },
      { name: "window_state", label: "window_state", kind: "select", options: ["open", "closed"], value: "open" },
      { name: "call_window", label: "call_window", kind: "text", value: "09:00-18:00" },
      { name: "transition_event", label: "transition_event", kind: "text", value: "" },
      { name: "attempt_count", label: "attempt_count", kind: "number", value: 0, min: 0, max: 3 },
      NOTES,
    ],
  },
  project_knowledge_grounding: {
    summary:
      "Answer a price / payment-plan / handover-date question from the project's own sheet, with the authority layer attached — or withhold the claim.",
    fields: [
      { name: "reference", label: "reference", kind: "text", value: "GRD-1001", required: true },
      STATUS,
      { name: "project_tag", label: "project_tag", kind: "text", value: "PSI-MARINA", required: true },
      {
        name: "claim_type",
        label: "claim_type",
        kind: "select",
        options: ["price", "payment_plan", "handover_date", "other"],
        value: "price",
        required: true,
      },
      {
        name: "question",
        label: "question",
        kind: "text",
        value: "What is the starting price of a one-bedroom at PSI Marina?",
        required: true,
      },
      AUTHORITY_FIELD,
      { name: "document_name", label: "document_name", kind: "text", value: "PSI Marina price sheet" },
      {
        name: "document_text",
        label: "document_text (ingested before the claim is judged)",
        kind: "textarea",
        value:
          "PSI Marina Residences — project sheet\nStarting price: AED 1,250,000 for a one-bedroom apartment.\nPayment plan: 40% during construction, 60% on handover.\nHandover date: Q1 2027.",
      },
      NOTES,
    ],
  },
  voice_gateway: {
    summary:
      "Originate an outbound call, or take a Twilio status callback keyed to the Call SID. The transport is stubbed offline; no socket is opened.",
    fields: [
      { name: "reference", label: "reference", kind: "text", value: "VGW-1001", required: true },
      STATUS,
      { name: "language", label: "language", kind: "select", options: ["en", "ar"], value: "en", required: true },
      { name: "direction", label: "direction", kind: "select", options: ["outbound", "inbound"], value: "outbound" },
      { name: "to_number", label: "to_number (originate)", kind: "text", value: "+971500001002" },
      { name: "from_number", label: "from_number", kind: "text", value: "+971400000000" },
      { name: "call_sid", label: "call_sid (status callback only)", kind: "text", value: "" },
      {
        name: "call_status",
        label: "call_status (empty = originate)",
        kind: "select",
        options: ["", "initiated", "ringing", "answered", "completed", "failed", "busy", "no-answer"],
        value: "",
      },
      { name: "twilio_mode", label: "twilio_mode", kind: "select", options: ["stubbed", "live"], value: "stubbed" },
      { name: "voice", label: "voice", kind: "text", value: "Polly.Joanna-Neural" },
      {
        name: "asr_engine",
        label: "asr_engine",
        kind: "select",
        options: ["twilio_gather_speech"],
        value: "twilio_gather_speech",
      },
      {
        name: "notes",
        label: "notes (spoken prompt on originate)",
        kind: "textarea",
        value: "Hello, this is the PSI Marina property line.",
      },
    ],
  },
  warm_transfer: {
    summary: "Bridge a qualified lead to the broker with a private whisper summary and a conference room.",
    fields: [
      { name: "reference", label: "reference", kind: "text", value: "XFER-1001", required: true },
      STATUS,
      CALL_SID,
      OUTCOME,
      {
        name: "summary",
        label: "summary (the broker's whisper)",
        kind: "textarea",
        value:
          "Noura Al-Farsi, PSI Marina one-bedroom, AED 1.25M, handover Q1 2027 — qualified and ready for the broker.",
        required: true,
      },
      { name: "broker_number", label: "broker_number (E.164)", kind: "text", value: "+971500001003" },
      { name: "lead_name", label: "lead_name", kind: "text", value: "Noura Al-Farsi" },
      { name: "conference_name", label: "conference_name", kind: "text", value: "" },
      { name: "whisper_text", label: "whisper_text", kind: "textarea", value: "" },
      {
        name: "transfer_status",
        label: "transfer_status",
        kind: "select",
        options: ["initiated", "bridged", "failed", "declined"],
        value: "initiated",
      },
      NOTES,
    ],
  },
  qualification_and_broker_summary: {
    summary:
      "Screen a finished call against the fixed outcome vocabulary and write the broker summary with the next action named.",
    fields: [
      { name: "reference", label: "reference", kind: "text", value: "QUAL-1001", required: true },
      STATUS,
      CALL_SID,
      OUTCOME,
      { name: "lead_name", label: "lead_name", kind: "text", value: "Noura Al-Farsi" },
      {
        name: "property_type",
        label: "property_type",
        kind: "select",
        options: ["apartment", "villa", "townhouse", "plot", "office"],
        value: "apartment",
      },
      { name: "budget", label: "budget", kind: "number", value: 1250000, min: 0 },
      { name: "area", label: "area", kind: "text", value: "Dubai Marina" },
      { name: "timeline", label: "timeline", kind: "text", value: "Q1 2027" },
      { name: "currency_setting", label: "currency_setting", kind: "text", value: "AED" },
      NOTES,
    ],
  },
  outcome_capture_and_ledger: {
    summary: "Append one call event to the audit ledger and sync the dialer's state with a vector clock.",
    fields: [
      { name: "reference", label: "reference", kind: "text", value: "LEDG-1001", required: true },
      STATUS,
      CALL_SID,
      {
        name: "event_type",
        label: "event_type",
        kind: "select",
        options: ["attempt", "answer", "outcome", "transfer", "disposition"],
        value: "outcome",
        required: true,
      },
      { ...OUTCOME, required: false },
      { name: "campaign", label: "campaign", kind: "text", value: "PSI-MARINA-Q4" },
      { name: "attempt_count", label: "attempt_count", kind: "number", value: 1, min: 0, max: 3 },
      { name: "ledger_index", label: "ledger_index", kind: "number", value: 0, min: 0 },
      NOTES,
    ],
  },
  crm_destination_placeholder: {
    summary:
      "The CRM attach point. Nothing is pushed until an operator names a system: an unnamed destination is recorded as stubbed, never invented.",
    fields: [
      { name: "reference", label: "reference", kind: "text", value: "CRM-1001", required: true },
      STATUS,
      {
        name: "crm_system",
        label: "crm_system",
        kind: "select",
        options: ["unstated", "salesforce", "hubspot", "zoho"],
        value: "salesforce",
        required: true,
      },
      { name: "destination_url", label: "destination_url", kind: "text", value: "https://crm.invalid/webhook/callops" },
      {
        name: "delivery_state",
        label: "delivery_state",
        kind: "select",
        options: ["queued", "stubbed", "refused"],
        value: "queued",
      },
      { name: "mock_mode", label: "mock_mode", kind: "bool", value: false },
      { name: "payload_shape", label: "payload_shape", kind: "textarea", value: "" },
      NOTES,
    ],
  },
  notification: {
    summary:
      "Ping the broker when a lead qualifies (or a transfer lands / a call fails): one delivery plus one notification event.",
    fields: [
      { name: "reference", label: "reference", kind: "text", value: "NOTIF-1001", required: true },
      STATUS,
      {
        name: "channel",
        label: "channel",
        kind: "select",
        options: ["email", "sms", "mcp", "webhook"],
        value: "mcp",
        required: true,
      },
      {
        name: "trigger_event",
        label: "trigger_event",
        kind: "select",
        options: ["lead_qualified", "transfer_completed", "call_failed", "campaign_summary"],
        value: "lead_qualified",
        required: true,
      },
      { name: "recipient", label: "recipient", kind: "text", value: "broker@psi-marina.example" },
      { name: "subject", label: "subject (blank = named by the trigger)", kind: "text", value: "" },
      {
        name: "message",
        label: "message",
        kind: "textarea",
        value: "Noura Al-Farsi qualified on PSI Marina (AED 1.25M, one-bedroom) — ready for a warm transfer.",
      },
      {
        name: "delivery_state",
        label: "delivery_state",
        kind: "select",
        options: ["queued", "sent", "failed"],
        value: "queued",
      },
      NOTES,
    ],
  },
  local_drive: {
    summary:
      "Read, write, list or delete one file inside the configured local drive root — path-confined, never outside it.",
    fields: [
      { name: "reference", label: "reference", kind: "text", value: "LDRV-1001", required: true },
      STATUS,
      { name: "relative_path", label: "relative_path", kind: "text", value: "calls/LDRV-1001.txt", required: true },
      {
        name: "operation",
        label: "operation",
        kind: "select",
        options: ["read", "write", "list", "delete"],
        value: "write",
        required: true,
      },
      { name: "root_path", label: "root_path (blank = configured root)", kind: "text", value: "" },
      {
        name: "content_preview",
        label: "content_preview",
        kind: "textarea",
        value: "PSI Marina — call LDRV-1001: qualified, broker summary attached.",
      },
      { name: "bytes_written", label: "bytes_written", kind: "number", value: 0, min: 0 },
      NOTES,
    ],
  },
  google_drive: {
    summary:
      "The Google Drive connector. Offline it runs stubbed and says so by name instead of reporting a transfer that never happened.",
    fields: [
      { name: "reference", label: "reference", kind: "text", value: "GDRV-1001", required: true },
      STATUS,
      {
        name: "GOOGLE_CLIENT_ID",
        label: "GOOGLE_CLIENT_ID (credential, required by this entity)",
        kind: "text",
        value: "",
        required: true,
      },
      {
        name: "GOOGLE_CLIENT_SECRET",
        label: "GOOGLE_CLIENT_SECRET (credential)",
        kind: "text",
        value: "",
        required: true,
      },
      {
        name: "GOOGLE_REFRESH_TOKEN",
        label: "GOOGLE_REFRESH_TOKEN (credential)",
        kind: "text",
        value: "",
        required: true,
      },
      {
        name: "drive_mode",
        label: "drive_mode",
        kind: "select",
        options: ["stubbed", "live"],
        value: "stubbed",
        required: true,
      },
      {
        name: "operation",
        label: "operation",
        kind: "select",
        options: ["upload", "download", "list"],
        value: "list",
        required: true,
      },
      { name: "folder_id", label: "folder_id", kind: "text", value: "root" },
      { name: "file_name", label: "file_name", kind: "text", value: "PSI-Marina-price-sheet.pdf" },
      { name: "credential_setting", label: "credential_setting", kind: "text", value: "" },
      NOTES,
    ],
  },
  mcp_adapter: {
    summary:
      "The MCP attach point: list the tool catalogue for a scope. Offline it falls back to the committed block contracts and names the fallback.",
    fields: [
      { name: "reference", label: "reference", kind: "text", value: "MCP-1001", required: true },
      STATUS,
      {
        name: "catalog_scope",
        label: "catalog_scope",
        kind: "select",
        options: ["platform", "vendor", "tenant"],
        value: "platform",
        required: true,
      },
      { name: "tool_name", label: "tool_name (blank = list)", kind: "text", value: "" },
      { name: "request_shape", label: "request_shape", kind: "textarea", value: "" },
      { name: "response_shape", label: "response_shape", kind: "textarea", value: "" },
      NOTES,
    ],
  },
};

/* ------------------------------------------------------------------ api */

async function request<T>(
  token: string,
  path: string,
  init?: { method?: string; body?: string },
): Promise<ApiResult<T>> {
  try {
    const response = await fetch(path, {
      method: (init && init.method) || "GET",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: init && init.body,
    });
    const text = await response.text();
    let body: T | null = null;
    if (text) {
      try {
        body = JSON.parse(text) as T;
      } catch {
        body = null;
      }
    }
    return { status: response.status, body };
  } catch (error) {
    return { status: 0, body: { ok: false, error: String(error) } as unknown as T };
  }
}

export function listCapabilities(token: string) {
  return request<{ items: CapabilityInfo[] }>(token, "/v1/capabilities");
}

export function listRecords(token: string, capability: string) {
  return request<Envelope>(token, `/v1/${capability}?limit=10&order=desc`);
}

export function getRecord(token: string, capability: string, id: number | string) {
  return request<Record<string, unknown>>(token, `/v1/${capability}/${id}`);
}

export function createRecord(token: string, capability: string, payload: unknown) {
  return request<Envelope>(token, `/v1/${capability}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/* ------------------------------------------------------- authority label */

export function authorityValue(value: unknown): AuthorityLabel | "" {
  const text = typeof value === "string" ? value.trim().toLowerCase() : "";
  return (AUTHORITY_LADDER as readonly string[]).includes(text) ? (text as AuthorityLabel) : "";
}

/** The authority layer behind an answer: the answer's own label first, then
 *  the label on the evidence hits that support it. */
export function authorityOf(body: unknown): AuthorityLabel | "" {
  const seen = new Set<unknown>();
  const queue: unknown[] = [body];
  let steps = 0;
  while (queue.length && steps < 400) {
    steps += 1;
    const node = queue.shift();
    if (!node || typeof node !== "object" || seen.has(node)) continue;
    seen.add(node);
    if (Array.isArray(node)) {
      node.forEach((item) => queue.push(item));
      continue;
    }
    const record = node as Record<string, unknown>;
    const own = authorityValue(record.authority_label) || authorityValue(record.authority);
    if (own) return own;
    Object.keys(record).forEach((key) => queue.push(record[key]));
  }
  return "";
}

/* The capability's own payload. The route answers
 * {ok, capability, result, stored}; `result` is the action envelope
 * (action_id / status / output) and the handler's fields -- answer,
 * authority_label, evidence, transition -- live in `result.output`. An
 * unwrapped answer carries them directly on `result`, so both are read. */
export function handlerPayload(body: unknown): Record<string, unknown> | null {
  if (!body || typeof body !== "object") return null;
  const envelope = (body as Record<string, unknown>).result;
  if (!envelope || typeof envelope !== "object") return null;
  const output = (envelope as Record<string, unknown>).output;
  if (output && typeof output === "object" && !Array.isArray(output)) {
    return output as Record<string, unknown>;
  }
  return envelope as Record<string, unknown>;
}

/* --------------------------------------------------------------- payloads */

export function buildPayload(spec: CapabilitySpec, values: Record<string, string>): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  spec.fields.forEach((field) => {
    const raw = values[field.name];
    if (field.kind === "bool") {
      payload[field.name] = raw === "true";
      return;
    }
    if (raw === undefined || String(raw).trim() === "") return;
    if (field.kind === "number") {
      const parsed = Number(raw);
      payload[field.name] = Number.isNaN(parsed) ? String(raw) : parsed;
      return;
    }
    payload[field.name] = String(raw);
  });
  return payload;
}

export function initialValues(spec: CapabilitySpec): Record<string, string> {
  const values: Record<string, string> = {};
  spec.fields.forEach((field) => {
    values[field.name] = field.value === undefined ? "" : String(field.value);
  });
  return values;
}

/* ------------------------------------------------------------ components */

const pill = (text: string, good: boolean) => (
  <span
    style={{
      border: `1px solid ${good ? "#16794a" : "#a3282f"}`,
      color: good ? "#16794a" : "#a3282f",
      borderRadius: 999,
      padding: "1px 8px",
      fontSize: 12,
      whiteSpace: "nowrap",
    }}
  >
    {text}
  </span>
);

const dim = { opacity: 0.72, fontSize: 13 } as const;
const card = { border: "1px solid #8883", borderRadius: 8, padding: 12, margin: "0 0 12px" } as const;
const mono = { background: "#6662", padding: 8, borderRadius: 6, overflow: "auto", maxHeight: 320, fontSize: 12 } as const;

export interface DeskProps {
  token: string;
}

export function CapabilityExplorer({ caps, onPick, onList }: {
  caps: CapabilityInfo[];
  onPick: (id: string) => void;
  onList: (id: string) => void;
}) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 12 }}>
      {caps.map((cap) => (
        <div key={cap.id} style={card}>
          <h3 style={{ margin: "0 0 6px", fontSize: 14, wordBreak: "break-all" }}>{cap.id}</h3>
          <div style={dim}>entity {cap.entity || "—"}</div>
          <div style={dim}>source {cap.source || "—"}</div>
          <div style={dim}>
            blocks: {cap.blocks && cap.blocks.length ? cap.blocks.join(", ") : "none declared"}
          </div>
          <div style={dim}>{cap.http && cap.http.create ? cap.http.create : "POST /v1/" + cap.id}</div>
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            <button type="button" onClick={() => onPick(cap.id)}>
              Open in desk
            </button>
            <button type="button" onClick={() => onList(cap.id)}>
              GET list
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

export function DeskForm({ spec, values, onChange, onSend, onReset }: {
  spec: CapabilitySpec;
  values: Record<string, string>;
  onChange: (name: string, value: string) => void;
  onSend: () => void;
  onReset: () => void;
}) {
  return (
    <div style={card}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <button type="button" onClick={onSend} style={{ fontWeight: 600, borderColor: "#16794a" }}>
          Send POST
        </button>
        <button type="button" onClick={onReset}>
          Reset values
        </button>
        <span style={dim}>{spec.summary}</span>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(250px, 1fr))", gap: 10, marginTop: 10 }}>
        {spec.fields.map((field) => (
          <label key={field.name} style={{ display: "flex", flexDirection: "column", gap: 3, fontSize: 12 }}>
            <span>
              {field.label}
              {field.required ? " *" : ""}
            </span>
            {field.kind === "select" ? (
              <select value={values[field.name] || ""} onChange={(e) => onChange(field.name, e.target.value)}>
                {(field.options || []).map((option) => (
                  <option key={option || "(empty)"} value={option}>
                    {option === "" ? "(empty)" : option}
                  </option>
                ))}
              </select>
            ) : field.kind === "textarea" ? (
              <textarea value={values[field.name] || ""} onChange={(e) => onChange(field.name, e.target.value)} />
            ) : field.kind === "bool" ? (
              <input
                type="checkbox"
                checked={values[field.name] === "true"}
                onChange={(e) => onChange(field.name, e.target.checked ? "true" : "false")}
              />
            ) : (
              <input
                type={field.kind === "number" ? "number" : "text"}
                value={values[field.name] || ""}
                onChange={(e) => onChange(field.name, e.target.value)}
              />
            )}
          </label>
        ))}
      </div>
    </div>
  );
}

export function ResponsePanel({ started, result, payload }: {
  started: string;
  result: ApiResult<Envelope> | null;
  payload: Record<string, unknown>;
}) {
  if (!result) return <p style={dim}>nothing sent yet</p>;
  const body = result.body;
  const okFlag = Boolean(body && body.ok === true);
  const label = authorityOf(body);
  const handler = handlerPayload(body) || {};
  const answer = typeof handler.answer === "string" ? handler.answer : "";
  const withheld = typeof handler.withheld_reason === "string" ? handler.withheld_reason : "";
  const question = typeof handler.question === "string" ? handler.question : "";
  const transition = handler.transition as Record<string, unknown> | undefined;
  const evidence = Array.isArray(handler.evidence)
    ? (handler.evidence as Array<Record<string, unknown>>)
    : [];
  const actionId = body && body.result && typeof body.result.action_id === "string"
    ? `${body.result.action_id} · ${String(body.result.status ?? "status unstated")}`
    : "";
  const signals: string[] = [];
  if (transition && typeof transition === "object") {
    signals.push(
      `transition: ${String(transition.from_state ?? "?")} -> ${String(transition.to_state ?? "?")}` +
        (transition.guard ? ` (guard ${String(transition.guard)})` : ""),
    );
  }
  if (typeof handler.call_sid === "string" && handler.call_sid) signals.push(`call_sid: ${handler.call_sid}`);
  if (handler.delivered !== undefined) {
    signals.push(
      `delivered: ${String(handler.delivered)} via ${String(handler.channel_used ?? "?")} (${String(
        handler.delivery_state ?? "?",
      )})`,
    );
  } else if (handler.delivery_state !== undefined) {
    signals.push(`delivery_state: ${String(handler.delivery_state)}`);
  }
  if (handler.recommended_action) {
    signals.push(
      `recommended_action: ${String(handler.recommended_action)}` +
        (handler.handoff_required ? " (handoff required)" : ""),
    );
  }
  if (handler.grounded !== undefined) {
    signals.push(
      `grounded: ${String(handler.grounded)}` +
        (handler.ingest_state ? ` · ingest ${String(handler.ingest_state)}` : ""),
    );
  }
  if (handler.tool_count !== undefined) {
    signals.push(`tools listed: ${String(handler.tool_count)} (source ${String(handler.catalog_source ?? "?")})`);
  }
  if (handler.transfer_status) signals.push(`transfer_status: ${String(handler.transfer_status)}`);
  if (handler.blocker) signals.push(`blocker: ${String(handler.blocker)}`);
  return (
    <div>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        {pill(okFlag ? "ok: true" : body && body.ok === false ? "ok: false" : `HTTP ${result.status}`, okFlag)}
        <span style={dim}>
          {started} → HTTP {result.status}
        </span>
        {actionId ? <span style={dim}>{actionId}</span> : null}
        {label ? pill(`authority: ${label}`, true) : null}
      </div>
      {result.status === 401 ? (
        <p style={{ color: "#a3282f" }}>
          HTTP 401 authentication_required — the bearer token was refused. Paste the platform token (dev default
          dev-local-token) and load again.
        </p>
      ) : null}
      {answer || withheld ? (
        <div style={{ borderLeft: `3px solid ${answer ? "#16794a" : "#a3282f"}`, padding: "6px 10px", marginTop: 10 }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
            {pill(`authority: ${label || "none returned"}`, Boolean(label))}
            {question ? <span style={dim}>{question}</span> : null}
          </div>
          {answer ? <p>{answer}</p> : null}
          {withheld ? <p style={{ color: "#a3282f" }}>withheld: {withheld}</p> : null}
          {evidence.length ? (
            <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 13 }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left" }}>citation</th>
                  <th style={{ textAlign: "left" }}>authority</th>
                  <th style={{ textAlign: "left" }}>score</th>
                </tr>
              </thead>
              <tbody>
                {evidence.map((hit, index) => (
                  <tr key={index}>
                    <td>{String(hit.citation || "—")}</td>
                    <td>{pill(`authority: ${authorityValue(hit.authority) || "unstated"}`, Boolean(authorityValue(hit.authority)))}</td>
                    <td>{hit.score === undefined ? "—" : String(hit.score)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </div>
      ) : null}
      {signals.length ? (
        <div style={dim}>
          {signals.map((line) => (
            <div key={line}>{line}</div>
          ))}
        </div>
      ) : null}
      <details open>
        <summary>request payload</summary>
        <pre style={mono}>{JSON.stringify(payload, null, 2)}</pre>
      </details>
      {body && body.error !== undefined ? (
        <details open>
          <summary>error</summary>
          <pre style={{ ...mono, color: "#a3282f" }}>{JSON.stringify(body.error, null, 2)}</pre>
        </details>
      ) : null}
      {body && body.result !== undefined ? (
        <details open>
          <summary>capability result</summary>
          <pre style={mono}>{JSON.stringify(handler, null, 2)}</pre>
        </details>
      ) : null}
      {body && body.result !== undefined ? (
        <details>
          <summary>action envelope (result)</summary>
          <pre style={mono}>{JSON.stringify(body.result, null, 2)}</pre>
        </details>
      ) : null}
      {body && body.stored !== undefined ? (
        <details open>
          <summary>stored — the row the route persisted</summary>
          <pre style={mono}>{JSON.stringify(body.stored, null, 2)}</pre>
        </details>
      ) : null}
    </div>
  );
}

export function RecentRecords({ capability, items, total, status, onRecord, onRefresh }: {
  capability: string;
  items: Array<Record<string, unknown>>;
  total: number;
  status: number | null;
  onRecord: (id: number) => void;
  onRefresh: () => void;
}) {
  return (
    <div style={card}>
      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
        <span style={dim}>
          GET /v1/{capability}?limit=10&amp;order=desc
          {status === null ? "" : ` → HTTP ${status} · ${items.length} shown of ${total} stored for this tenant`}
        </span>
        <button type="button" onClick={onRefresh}>
          Reload records
        </button>
      </div>
      {items.length === 0 ? (
        <p style={dim}>No records for this capability yet — send one and it will appear here.</p>
      ) : (
        <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 13 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left" }}>id</th>
              <th style={{ textAlign: "left" }}>reference</th>
              <th style={{ textAlign: "left" }}>status</th>
              <th style={{ textAlign: "left" }}>authority</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const label = authorityValue(item.authority_label);
              const id = Number(item.id);
              return (
                <tr key={String(item.id)}>
                  <td>{String(item.id)}</td>
                  <td>{String(item.reference ?? "—")}</td>
                  <td>{String(item.status ?? "—")}</td>
                  <td>{label ? `authority: ${label}` : "—"}</td>
                  <td>
                    <button type="button" onClick={() => onRecord(id)}>
                      GET /{"{id}"}
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ app */

export default function App() {
  const [token, setToken] = useState("dev-local-token");
  const [caps, setCaps] = useState<CapabilityInfo[]>([]);
  const [capsStatus, setCapsStatus] = useState("not loaded");
  const [selected, setSelected] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [response, setResponse] = useState<ApiResult<Envelope> | null>(null);
  const [started, setStarted] = useState("");
  const [records, setRecords] = useState<Array<Record<string, unknown>>>([]);
  const [recordTotal, setRecordTotal] = useState(0);
  const [recordStatus, setRecordStatus] = useState<number | null>(null);
  const [recordDetail, setRecordDetail] = useState<Record<string, unknown> | null>(null);

  const spec = useMemo(() => (selected ? CAPABILITY_FIELDS[selected] : undefined), [selected]);

  const load = useCallback(async () => {
    const result = await listCapabilities(token);
    const items = result.body && result.body.items ? result.body.items : [];
    setCaps(items);
    setCapsStatus(
      result.status === 200 ? `${items.length} capabilities served` : `GET /v1/capabilities answered HTTP ${result.status}`,
    );
    if (items.length && !selected) {
      const first = items[0].id;
      setSelected(first);
      setValues(CAPABILITY_FIELDS[first] ? initialValues(CAPABILITY_FIELDS[first]) : {});
    }
  }, [token, selected]);

  const loadRecords = useCallback(
    async (capability: string) => {
      if (!capability) return;
      const result = await listRecords(token, capability);
      setRecordStatus(result.status);
      setRecords(result.body && Array.isArray(result.body.items) ? result.body.items : []);
      setRecordTotal(result.body && typeof result.body.total === "number" ? result.body.total : 0);
    },
    [token],
  );

  useEffect(() => {
    void load();
  }, [load]);

  const pick = useCallback((id: string) => {
    setSelected(id);
    setValues(CAPABILITY_FIELDS[id] ? initialValues(CAPABILITY_FIELDS[id]) : {});
    setResponse(null);
    setRecordDetail(null);
    setRecordStatus(null);
    setRecords([]);
  }, []);

  const send = useCallback(async () => {
    if (!spec || !selected) return;
    const payload = buildPayload(spec, values);
    setStarted(`POST /v1/${selected}`);
    const result = await createRecord(token, selected, payload);
    setResponse(result);
    if (result.body && result.body.ok === true) {
      await loadRecords(selected);
    }
  }, [spec, selected, values, token, loadRecords]);

  const fetchRecord = useCallback(
    async (id: number) => {
      const result = await getRecord(token, selected, id);
      setRecordDetail(result.body);
    },
    [token, selected],
  );

  return (
    <main style={{ font: "15px/1.5 system-ui, -apple-system, sans-serif", padding: 24, maxWidth: 1120, margin: "0 auto" }}>
      <h1 style={{ fontSize: 21, margin: "0 0 4px" }}>CallOps — operations desk</h1>
      <p style={dim}>
        Outbound AI voice-calling for the brokerage. This desk discovers the platform's capabilities and drives them
        over their real routes (POST /v1/&lt;capability&gt;, GET /v1/&lt;capability&gt;, GET /v1/&lt;capability&gt;/&#123;id&#125;)
        with your bearer token.
      </p>
      <div style={card}>
        <label>
          Bearer token{" "}
          <input type="password" value={token} onChange={(e) => setToken(e.target.value)} />
        </label>{" "}
        <button type="button" onClick={() => void load()}>
          Load capabilities
        </button>{" "}
        <span style={dim}>{capsStatus}</span>
      </div>

      <h2 style={{ fontSize: 16 }}>Capabilities discovered</h2>
      <CapabilityExplorer caps={caps} onPick={pick} onList={(id) => void loadRecords(id)} />

      <h2 style={{ fontSize: 16 }}>Operations desk</h2>
      <div style={card}>
        <label>
          Capability{" "}
          <select value={selected} onChange={(e) => pick(e.target.value)}>
            {caps.map((cap) => (
              <option key={cap.id} value={cap.id}>
                {cap.id}
              </option>
            ))}
          </select>
        </label>
      </div>
      {spec ? (
        <DeskForm
          spec={spec}
          values={values}
          onChange={(name, value) => setValues((prev) => ({ ...prev, [name]: value }))}
          onSend={() => void send()}
          onReset={() => setValues(initialValues(spec))}
        />
      ) : (
        <p style={dim}>No field list is hard-coded for this capability.</p>
      )}

      <h2 style={{ fontSize: 16 }}>Response</h2>
      <div style={card}>
        <ResponsePanel started={started} result={response} payload={spec ? buildPayload(spec, values) : {}} />
      </div>

      <h2 style={{ fontSize: 16 }}>Recent records</h2>
      <RecentRecords
        capability={selected}
        items={records}
        total={recordTotal}
        status={recordStatus}
        onRecord={(id) => void fetchRecord(id)}
        onRefresh={() => void loadRecords(selected)}
      />
      {recordDetail ? (
        <div style={card}>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {pill("HTTP 200", true)}
            <span style={dim}>
              GET /v1/{selected}/{String(recordDetail.id)}
            </span>
            {authorityOf(recordDetail) ? pill(`authority: ${authorityOf(recordDetail)}`, true) : null}
          </div>
          <pre style={mono}>{JSON.stringify(recordDetail, null, 2)}</pre>
        </div>
      ) : null}
    </main>
  );
}
