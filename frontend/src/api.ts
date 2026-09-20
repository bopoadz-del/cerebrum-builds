/**
 * Thin typed client over the platform's own routes.
 *
 * Written by the factory WRITER role (codewhale exec)
 *
 * The UI drives the SAME HTTP surface the harness drives: there is no second
 * API, no mock, and no local state that pretends a write happened. Every call
 * returns the platform's envelope so a refusal is shown as a refusal.
 */

export type Envelope = {
  ok?: boolean;
  error?: string;
  items?: Array<Record<string, unknown>>;
  total?: number;
  [key: string]: unknown;
};

let token = "";

export function setToken(value: string): void {
  token = value;
}

export function getToken(): string {
  return token;
}

export async function call(
  path: string,
  init: RequestInit = {},
): Promise<{ status: number; body: Envelope }> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(path, { ...init, headers });
  let body: Envelope = {};
  try {
    body = (await res.json()) as Envelope;
  } catch {
    body = {};
  }
  return { status: res.status, body };
}

export async function listCapabilities(): Promise<string[]> {
  const res = await call("/v1/capabilities");
  const items = (res.body.items as Array<Record<string, unknown>> | undefined) ?? [];
  return items
    .map((item) => String(item.id ?? item.capability_id ?? ""))
    .filter(Boolean);
}

export async function createRecord(
  capability: string,
  record: Record<string, unknown>,
): Promise<Envelope> {
  const res = await call(`/v1/${capability}`, {
    method: "POST",
    body: JSON.stringify(record),
  });
  return { status: res.status, ...res.body } as Envelope;
}

export async function listRecords(capability: string): Promise<Envelope> {
  const res = await call(`/v1/${capability}`);
  return res.body;
}

/** The precedence.v1 ladder, so a screen can show where an answer came from. */
export async function authorityLadder(): Promise<Envelope> {
  const res = await call("/v1/authority");
  return res.body;
}
