/**
 * Management console shell for the Dubai schools estate.
 *
 * Written by the factory WRITER role (codewhale exec)
 *
 * The shell owns the token, the capability roster and the three modules the
 * product declares (command_center, operational_chat, resident_engineer).
 * It calls only the platform's own routes through ./api -- there is no
 * second API and nothing here fabricates a stored record.
 */

import React, { useCallback, useEffect, useState } from "react";
import { authorityLadder, listCapabilities, setToken } from "./api";
import CommandCenter from "./modules/command_center";
import OperationalChat from "./modules/operational_chat";
import ResidentEngineer from "./modules/resident_engineer";

type Tab = "command" | "chat" | "engineer";

const TABS: Array<{ id: Tab; label: string }> = [
  { id: "command", label: "Command centre" },
  { id: "chat", label: "Operational chat" },
  { id: "engineer", label: "Resident engineer" },
];

export default function App(): JSX.Element {
  const [token, setTokenValue] = useState<string>("");
  const [connected, setConnected] = useState<boolean>(false);
  const [capabilities, setCapabilities] = useState<string[]>([]);
  const [authority, setAuthority] = useState<Record<string, unknown> | null>(null);
  const [tab, setTab] = useState<Tab>("command");

  const connect = useCallback(async (): Promise<void> => {
    setToken(token);
    const ids = await listCapabilities();
    setCapabilities(ids);
    setConnected(ids.length > 0);
    setAuthority(await authorityLadder());
  }, [token]);

  useEffect(() => {
    // A pre-seeded token (the pilot's dev-local-token) still has to be
    // confirmed against the live route before any screen claims a connection.
    if (token) void connect();
  }, [token, connect]);

  return (
    <main className="console">
      <header>
        <h1>Facility Management Platform for Schools</h1>
        <p className="dim">
          Ten schools across Dubai. Complaints, teams, dashboards, reports and
          access — all served by this platform&apos;s own routes.
        </p>
      </header>

      <section className="card">
        <label htmlFor="token">Bearer token</label>
        <input
          id="token"
          type="password"
          value={token}
          onChange={(event) => setTokenValue(event.target.value)}
          placeholder="platform token"
        />
        <button type="button" onClick={() => void connect()}>
          Connect
        </button>
        <span className="dim">
          {connected ? `${capabilities.length} capability(ies)` : "not connected"}
        </span>
      </section>

      {authority ? (
        <p className="dim">
          Answer authority: {String(authority.version)} — layer{" "}
          {String((authority.label as Record<string, unknown>)?.layer ?? "formulas")}
        </p>
      ) : null}

      <nav>
        {TABS.map((entry) => (
          <button
            key={entry.id}
            type="button"
            aria-pressed={tab === entry.id}
            onClick={() => setTab(entry.id)}
          >
            {entry.label}
          </button>
        ))}
      </nav>

      {tab === "command" ? <CommandCenter capabilities={capabilities} /> : null}
      {tab === "chat" ? <OperationalChat capabilities={capabilities} /> : null}
      {tab === "engineer" ? <ResidentEngineer capabilities={capabilities} /> : null}
    </main>
  );
}
