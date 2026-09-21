/**
 * The one API this console talks to: the platform's own routes.
 *
 * There is no second backend and no client-side mock: every function below
 * calls a real route, with the caller's platform token, and returns what the
 * platform answered. The tenant is never sent by the client -- it is resolved
 * from the bearer token on the server (app/tenancy.py).
 */
export type PlatformToken = string;

export interface ApiResult<T> {
  status: number;
  body: T | null;
}

export interface Capability {
  id: string;
  entity: string;
  blocks?: string[];
  http?: Record<string, string>;
}

export interface RetrievedHit {
  title?: string;
  authority?: string;
  score?: number;
  text?: string;
}

export interface AnswerEnvelope {
  answer: string | null;
  refused?: boolean;
  reason?: string;
  authority?: string;
  rank?: number;
  precedence?: string;
  citations?: RetrievedHit[];
  hits?: RetrievedHit[];
}

async function request<T>(
  token: PlatformToken,
  path: string,
  init?: RequestInit,
): Promise<ApiResult<T>> {
  const response = await fetch(path, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...((init && init.headers) || {}),
    },
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
}

export function listCapabilities(token: PlatformToken) {
  return request<{ items: Capability[] }>(token, "/v1/capabilities");
}

export function listRecords<T>(token: PlatformToken, capability: string) {
  return request<{ items: T[]; total: number }>(token, `/v1/${capability}`);
}

export function createRecord<T>(token: PlatformToken, capability: string, payload: unknown) {
  return request<T>(token, `/v1/${capability}`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function ingestDocument(
  token: PlatformToken,
  input: { title: string; kind: string; text: string; authority?: string },
) {
  return request<{ ok: boolean; document_id: number; chunks: number; authority: string }>(
    token,
    "/v1/rag/ingest",
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function askCorpus(token: PlatformToken, question: string, topK = 4) {
  return request<AnswerEnvelope>(token, "/v1/rag/query", {
    method: "POST",
    body: JSON.stringify({ q: question, top_k: topK }),
  });
}

export function recordFolioCharge(
  token: PlatformToken,
  input: {
    reference: string;
    setting: string;
    folio_reference: string;
    charge_type: string;
    amount: number;
    tax_rate_percent?: number;
  },
) {
  return request<{ ok: boolean; result?: { folio?: Record<string, unknown> } }>(
    token,
    "/v1/operations_billing",
    { method: "POST", body: JSON.stringify({ status: "open", ...input }) },
  );
}
