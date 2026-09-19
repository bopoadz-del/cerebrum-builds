/* VetClinic Operations Platform — operator console.
 *
 * Calls the live backend: GET /health, GET /v1/capabilities and the
 * per-capability POST/GET routes under /v1/<capability_id>. No second API,
 * no mock data: every row rendered here came back from app/routes.py.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import CommandCenterModule from "./modules/command_center";
import KnowledgeBaseModule from "./modules/knowledge_base";
import OperationalChatModule from "./modules/operational_chat";
import ResidentEngineerModule from "./modules/resident_engineer";

const PRODUCT_ID = "veterinary-practice";
const PLATFORM_TOKEN =
  (import.meta as unknown as { env?: Record<string, string> }).env
    ?.VITE_PLATFORM_TOKEN || "dev-local-token";

export const authHeaders = (): Record<string, string> => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${PLATFORM_TOKEN}`,
});

export interface Capability {
  id: string;
  entity: string;
  http?: Record<string, string>;
}

export function useCapabilities(): {
  capabilities: Capability[];
  error: string;
} {
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    fetch("/v1/capabilities", { headers: authHeaders() })
      .then((r) => r.json())
      .then((body) => setCapabilities((body?.items as Capability[]) || []))
      .catch((exc) => setError(String(exc)));
  }, []);
  return { capabilities, error };
}

export function useRecords(capabilityId: string) {
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [status, setStatus] = useState("idle");

  const refresh = useCallback(() => {
    if (!capabilityId) return;
    setStatus("loading");
    fetch(`/v1/${capabilityId}?limit=25`, { headers: authHeaders() })
      .then((r) => r.json())
      .then((body) => {
        const items = (body?.items as Record<string, unknown>[]) || [];
        setRows(items);
        setStatus(items.length ? "ready" : "empty");
      })
      .catch((exc) => {
        setStatus("error");
        setRows([]);
        void exc;
      });
  }, [capabilityId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const create = useCallback(
    async (payload: Record<string, unknown>) => {
      const resp = await fetch(`/v1/${capabilityId}`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify(payload),
      });
      const body = await resp.json().catch(() => ({}));
      if (!resp.ok || body?.ok === false) {
        return { ok: false, error: String(body?.error || body?.detail || resp.status) };
      }
      refresh();
      return { ok: true, stored: body?.stored };
    },
    [capabilityId, refresh],
  );

  return { rows, status, refresh, create };
}

export default function App() {
  const { capabilities, error } = useCapabilities();
  const tabs = useMemo(
    () => ["command_center", "operational_chat", "knowledge_base", "resident_engineer"],
    [],
  );
  const [tab, setTab] = useState(tabs[0]);

  return (
    <main data-product={PRODUCT_ID}>
      <header>
        <h1>VetClinic Operations Platform</h1>
        <p>
          Animal patient records, appointments, clinical notes and prescriptions,
          vaccination tracking, billing and client reminders — one practice console.
        </p>
      </header>
      <nav>
        {tabs.map((name) => (
          <button key={name} onClick={() => setTab(name)} aria-pressed={tab === name}>
            {name.replace("_", " ")}
          </button>
        ))}
      </nav>
      {error ? <p role="alert">{error}</p> : null}
      {tab === "command_center" ? <CommandCenterModule capabilities={capabilities} /> : null}
      {tab === "operational_chat" ? <OperationalChatModule capabilities={capabilities} /> : null}
      {tab === "knowledge_base" ? <KnowledgeBaseModule /> : null}
      {tab === "resident_engineer" ? <ResidentEngineerModule /> : null}
    </main>
  );
}
