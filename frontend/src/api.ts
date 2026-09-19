// Typed client for the Bakery Chain Operations & Delivery Platform HTTP surface.
// Written by the factory WRITER role (codewhale exec)
// Every call goes to the live capability routes; there is no second API.

export const CAPABILITIES = [
  "stock_inventory_management",
  "delivery_dispatch_tracking",
  "document_knowledge_qa",
  "fleet_cost_and_pricing",
  "management_reporting_dashboard",
  "user_roles_workforce",
  "operational_procedures_readiness",
  "audit_evidence_trail",
] as const;

export type CapabilityId = (typeof CAPABILITIES)[number];

export type Record = { id?: number; reference?: string; status?: string } & globalThis.Record<
  string,
  string | number | boolean | null | undefined
>;

export type Job = {
  kernel: string;
  title: string;
  agent: string;
  mandate: string;
  http_routes: string[];
};

export type GateSuiteItem = { file: string; covers: string; marker?: string };

export function token(): string {
  return localStorage.getItem("bakery_token") ?? "dev-local-token";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token()}`,
      ...(init?.headers ?? {}),
    },
  });
  const body = (await response.json()) as T;
  if (!response.ok) {
    throw new Error(`${path}: HTTP ${response.status}`);
  }
  return body;
}

export function health() {
  return request<{ status: string; ok: boolean }>("/health");
}

export function list(capability: CapabilityId) {
  return request<{ items?: Record[]; total?: number }>(`/v1/${capability}`);
}

export function create(capability: CapabilityId, body: globalThis.Record<string, unknown>) {
  return request<{ ok?: boolean; record?: Record; error?: string }>(`/v1/${capability}`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getJobs() {
  return request<{ jobs: Job[] }>("/v1/jobs");
}

export function getGates() {
  return request<{ suite: GateSuiteItem[] }>("/v1/gates");
}

export function queryRag(question: string) {
  return request<{ items?: Record[]; hit_count?: number }>(
    `/v1/rag/query?q=${encodeURIComponent(question)}`,
  ).catch(() => ({ items: [] }));
}

export function ingestRag(text: string) {
  return request<{ ok?: boolean }>("/v1/rag/ingest", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}
