/**
 * Hotel Operations operator console.
 *
 * One console, driving the platform's real routes: the capability explorer
 * lists what the build ships and posts a record into any of them; the
 * documents module ingests a manual/SOP and answers a question from it, always
 * showing the authority layer the answer came from (precedence.v1); the folio
 * module records a charge and reports the operator's own currency/tax setting.
 */
import { useCallback, useEffect, useState } from "react";
import {
  AnswerEnvelope,
  Capability,
  askCorpus,
  createRecord,
  ingestDocument,
  listCapabilities,
  listRecords,
  recordFolioCharge,
} from "./api";
import CommandCenter from "./modules/command_center";
import OperationalChat from "./modules/operational_chat";
import ResidentEngineer from "./modules/resident_engineer";

export default function App() {
  const [token, setToken] = useState("");
  const [caps, setCaps] = useState<Capability[]>([]);
  const [status, setStatus] = useState("paste a platform token, then load the capabilities");

  const load = useCallback(async () => {
    const result = await listCapabilities(token);
    if (result.status !== 200 || !result.body) {
      setCaps([]);
      setStatus(`GET /v1/capabilities answered ${result.status} — check the token`);
      return;
    }
    setCaps(result.body.items || []);
    setStatus(`${(result.body.items || []).length} capabilities served`);
  }, [token]);

  useEffect(() => {
    if (token) {
      void load();
    }
  }, [load, token]);

  return (
    <main style={{ font: "15px/1.5 system-ui, sans-serif", padding: 24, maxWidth: 1100, margin: "0 auto" }}>
      <h1 style={{ fontSize: 20, marginBottom: 4 }}>Hotel Operations</h1>
      <p style={{ opacity: 0.7, fontSize: 13 }}>{status}</p>
      <label>
        Bearer token{" "}
        <input type="password" value={token} onChange={(e) => setToken(e.target.value)} />
      </label>
      <CommandCenter capabilities={caps} token={token} />
      <OperationalChat token={token} />
      <ResidentEngineer />
      <details>
        <summary>Raw capability responses</summary>
        <pre style={{ maxHeight: 320, overflow: "auto" }}>{JSON.stringify(caps, null, 2)}</pre>
      </details>
    </main>
  );
}

export const consoleRoutes = {
  listCapabilities,
  listRecords,
  createRecord,
  ingestDocument,
  askCorpus,
  recordFolioCharge,
};

export type { AnswerEnvelope, Capability };
