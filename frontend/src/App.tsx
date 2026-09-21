import { useCallback, useEffect, useState } from "react";
import { Api, type Capability, type Authority } from "./api";
import { CommandCenter } from "./modules/command_center";
import { OperationalChat } from "./modules/operational_chat";
import { ResidentEngineer } from "./modules/resident_engineer";

export function layerBadge(authority?: Authority) {
  if (!authority?.label) return null;
  const layer = authority.label.split(":")[0];
  return <span className={`badge ${layer}`}>{authority.label}</span>;
}

export default function App() {
  const [token, setToken] = useState("dev-local-token");
  const [campaign, setCampaign] = useState("psi-q3");
  const [tenant, setTenant] = useState<string>("");
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [api, setApi] = useState<Api>(() => new Api("dev-local-token"));
  const [error, setError] = useState("");

  const connect = useCallback(async () => {
    const client = new Api(token);
    setApi(client);
    const who = await client.whoami();
    if (!who.ok) {
      setError(`not connected (HTTP ${who.status})`);
      setTenant("");
      return;
    }
    setError("");
    setTenant(who.payload.tenant.tenant_id);
    const caps = await client.capabilities();
    if (caps.ok) setCapabilities(caps.payload.capabilities);
  }, [token]);

  useEffect(() => {
    void connect();
  }, [connect]);

  return (
    <div className="app">
      <header>
        <h1>CallOps <span className="dim">— outbound calling console for PSI</span></h1>
        <div className="dim">
          Every answer shows the authority layer it came from (precedence.v1:
          certified &gt; documents &gt; formulas &gt; procedures).
        </div>
        <div className="row">
          <label>
            Bearer token
            <input value={token} onChange={(event) => setToken(event.target.value)} />
          </label>
          <label>
            Campaign
            <input value={campaign} onChange={(event) => setCampaign(event.target.value)} />
          </label>
          <button onClick={() => void connect()}>Connect</button>
          <span className={error ? "err" : "dim"}>{error || (tenant ? `tenant ${tenant}` : "not connected")}</span>
        </div>
      </header>

      <CommandCenter api={api} campaign={campaign} capabilities={capabilities} />
      <OperationalChat api={api} campaign={campaign} />
      <ResidentEngineer api={api} />
    </div>
  );
}
