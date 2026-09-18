// One API client for every panel: the live platform routes.
export const TOKEN_STORAGE_KEY = "front-desk-token";

export function token(): string {
  return localStorage.getItem(TOKEN_STORAGE_KEY) || "dev-local-token";
}

export function setToken(value: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, value);
}

function headers(): Record<string, string> {
  return { "Content-Type": "application/json", Authorization: `Bearer ${token()}` };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, headers: headers() });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(String((body as { error?: string }).error || response.statusText));
  }
  return body as T;
}

export type CheckIn = {
  id: number;
  reference: string;
  guest_name: string;
  room_number: string;
  nights: number;
  arrival_time: string;
  status: string;
  notes?: string;
};

export type BoardRow = {
  id: number;
  guest_name: string;
  room_number: string;
  arrival_date: string;
  arrived: boolean;
};

export type Availability = {
  availability: { room_number: string; nights: number; is_available: boolean };
  stay: { estimated_charge: number | null; currency: string };
};

export function listCheckins(): Promise<{ items: CheckIn[]; total: number }> {
  return request("/v1/record_checkin");
}

export function recordCheckIn(payload: Record<string, unknown>): Promise<{ ok: boolean }> {
  return request("/v1/record_checkin", { method: "POST", body: JSON.stringify(payload) });
}

export function checkArrivals(): Promise<{ items: BoardRow[]; total: number }> {
  return request("/v1/todays_arrivals_board");
}

export function checkAvailability(payload: Record<string, unknown>): Promise<Availability> {
  return request("/v1/room_availability_check", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function vendorHealth(): Promise<{ ok: boolean; unavailable: string[] }> {
  return request("/v1/vendor_health");
}

export type RAGHit = {
  id: number;
  title: string;
  excerpt: string;
  layer: string;
  certified: boolean;
  score: number;
};

export function ingestDocument(text: string, title?: string): Promise<{ ok: boolean; id: number }> {
  return request("/v1/rag/ingest", {
    method: "POST",
    body: JSON.stringify({ text, title: title || undefined, source_kind: "document" }),
  });
}

export function askHouse(q: string): Promise<{ ok: boolean; hits: RAGHit[]; total: number }> {
  return request("/v1/rag/query", { method: "POST", body: JSON.stringify({ q }) });
}
