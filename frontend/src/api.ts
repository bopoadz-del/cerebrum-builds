/**
 * Hotel Front Desk Log UI -> platform HTTP client.
 *
 * Written by the factory WRITER role (codewhale exec)
 *
 * Every call goes to the live API the backend serves (POST/GET /v1/<capability>,
 * GET /v1/<capability>/<id>, GET /v1/vendor_health, GET /v1/notification_outbox).
 * The UI never invents a second API and never fabricates a record locally.
 */

export const PLATFORM_TOKEN_STORAGE_KEY = "hotel-front-desk.token";

export function platformToken(): string {
  const stored = window.localStorage.getItem(PLATFORM_TOKEN_STORAGE_KEY);
  return stored && stored.trim() ? stored.trim() : "dev-local-token";
}

export function setPlatformToken(token: string): void {
  window.localStorage.setItem(PLATFORM_TOKEN_STORAGE_KEY, token.trim());
}

export type Json = Record<string, unknown>;

export type Capability = {
  id: string;
  entity: string;
  source: string;
  http: Record<string, string>;
};

export type ListPayload = {
  items?: Json[];
  total?: number;
  ok?: boolean;
  error?: string;
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", "Bearer " + platformToken());
  headers.set("Accept", "application/json");
  if (init.body) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { ...init, headers });
  const text = await response.text();
  const body = text ? JSON.parse(text) : {};
  if (!response.ok) {
    const detail = typeof body?.detail === "string" ? body.detail : response.statusText;
    throw new Error(`${response.status} ${detail}`);
  }
  return body as T;
}

export function listCapabilities(): Promise<{ items: Capability[] }> {
  return request<{ items: Capability[] }>("/v1/capabilities");
}

export function listRecords(capability: string, limit = 25): Promise<ListPayload> {
  return request<ListPayload>(`/v1/${capability}?limit=${limit}`);
}

export function getRecord(capability: string, id: number): Promise<Json> {
  return request<Json>(`/v1/${capability}/${id}`);
}

export function createRecord(capability: string, record: Json): Promise<Json> {
  return request<Json>(`/v1/${capability}`, {
    method: "POST",
    body: JSON.stringify(record),
  });
}

export function vendorHealth(): Promise<Json> {
  return request<Json>("/v1/vendor_health");
}

export function notificationOutbox(): Promise<ListPayload> {
  return request<ListPayload>("/v1/notification_outbox");
}

export function health(): Promise<Json> {
  return request<Json>("/health");
}

export function isRefusal(body: Json | null | undefined): boolean {
  return !!body && (body as { ok?: boolean }).ok === false;
}

export function refusalReason(body: Json | null | undefined): string {
  if (!body) return "";
  const error = (body as { error?: unknown }).error;
  return typeof error === "string" ? error : "";
}
