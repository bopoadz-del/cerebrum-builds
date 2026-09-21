/**
 * CallOps API client.
 *
 * One place knows the platform's routes, and it is the platform's own: the
 * capability surface is discovered from GET /v1/capabilities and every call
 * carries the operator's bearer token. There is no mock, no fixture and no
 * second backend -- a refusal surfaces the platform's own error text.
 *
 * The served console is app/static/index.html; this module is the React
 * source for the same desk.
 */

export interface CapabilityInfo {
  id: string;
  entity?: string;
  source?: string;
  blocks?: string[];
  http?: Record<string, string>;
}

export interface CapabilityList {
  items: CapabilityInfo[];
}

export type Payload = Record<string, unknown>;

export class ApiRefused extends Error {
  constructor(message: string, readonly status: number, readonly body: unknown) {
    super(message);
    this.name = "ApiRefused";
  }
}

const DEFAULT_TOKEN = "dev-local-token";
let token = DEFAULT_TOKEN;

export function setToken(value: string): void {
  token = value.trim() || DEFAULT_TOKEN;
}

export function currentToken(): string {
  return token;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(body === undefined ? {} : { "Content-Type": "application/json" }),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  let parsed: unknown = null;
  try {
    parsed = text ? JSON.parse(text) : null;
  } catch {
    parsed = text;
  }
  if (!response.ok) {
    throw new ApiRefused(`${method} ${path} answered ${response.status}`, response.status, parsed);
  }
  return parsed as T;
}

/** Which capabilities this platform serves, from the platform itself. */
export function listCapabilities(): Promise<CapabilityList> {
  return request<CapabilityList>("GET", "/v1/capabilities");
}

/** POST one record. The route persists it for the caller's tenant. */
export function createRecord<T = Record<string, unknown>>(
  capabilityId: string,
  payload: Payload,
): Promise<T> {
  return request<T>("POST", `/v1/${capabilityId}`, payload);
}

/** Re-read what was stored, so a write is visible rather than claimed. */
export function listRecords<T = Record<string, unknown>>(
  capabilityId: string,
): Promise<T> {
  return request<T>("GET", `/v1/${capabilityId}`);
}

/** Ingest a project sheet into the tenant corpus (cite-or-refuse needs it). */
export function ingestDocument(
  title: string,
  text: string,
  authorityLabel = "documents",
): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("POST", "/v1/rag/ingest", {
    title,
    text,
    authority_label: authorityLabel,
  });
}

/** Ask a grounded question. The answer carries its authority label. */
export function queryCorpus(question: string): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(
    "GET",
    `/v1/rag/query?q=${encodeURIComponent(question)}`,
  );
}

/** precedence.v1 — the ladder every retrieved answer is labelled with. */
export const AUTHORITY_LADDER = ["certified", "documents", "formulas", "procedures"] as const;
export type AuthorityLabel = (typeof AUTHORITY_LADDER)[number];
