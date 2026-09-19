// Typed client for the platform's live HTTP surface. No mock data: every
// function posts to the route the backend actually serves.

export type Capability = {
  id: string;
  entity: string;
  http: { create: string; list: string; get: string; update?: string; delete?: string };
};

export type PlatformRecord = Record<string, unknown> & { id?: number };

const TOKEN_KEY = 'finops.platform.token';

export function platformToken(): string {
  return localStorage.getItem(TOKEN_KEY) || 'dev-local-token';
}

export function setPlatformToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${platformToken()}`,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(`${method} ${path} → HTTP ${response.status}: ${text.slice(0, 200)}`);
  }
  if (payload && payload.ok === false) {
    throw new Error(String(payload.error || 'the capability refused the request'));
  }
  return payload as T;
}

export const api = {
  capabilities: () => request<{ items: Capability[] }>('GET', '/v1/capabilities'),
  health: () => request<Record<string, unknown>>('GET', '/health'),
  list: (capability: string) =>
    request<{ items: PlatformRecord[]; total: number }>('GET', `/v1/${capability}`),
  create: (capability: string, record: PlatformRecord) =>
    request<{ ok: boolean; stored: PlatformRecord }>('POST', `/v1/${capability}`, record),
  read: (capability: string, id: number) =>
    request<PlatformRecord>('GET', `/v1/${capability}/${id}`),
  ask: (question: string) =>
    request<{ answer: string; citations: unknown[]; hits: unknown[] }>(
      'POST',
      '/v1/rag/query',
      { q: question },
    ),
  ingest: (text: string, documentType: string) =>
    request<{ ok: boolean; ingested: PlatformRecord }>('POST', '/v1/rag/ingest', {
      text,
      document_type: documentType,
    }),
};
