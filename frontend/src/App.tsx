/**
 * Hotel Front Desk Log shell.
 *
 * Written by the factory WRITER role (codewhale exec)
 *
 * Three panels over the live platform API: the command centre (capability
 * records), operational chat (deterministic triage into the owning
 * capability) and the resident engineer (health, vendor slices, outbox).
 * There is no second API and no client-side store.
 */
import React, { useState } from "react";
import CommandCenter from "./modules/command_center";
import OperationalChat from "./modules/operational_chat";
import ResidentEngineer from "./modules/resident_engineer";
import { PLATFORM_TOKEN_STORAGE_KEY, platformToken, setPlatformToken } from "./api";

type Tab = "command_center" | "operational_chat" | "resident_engineer";

const TABS: Array<{ id: Tab; label: string }> = [
  { id: "command_center", label: "Command centre" },
  { id: "operational_chat", label: "Operational chat" },
  { id: "resident_engineer", label: "Resident engineer" },
];

export default function App(): JSX.Element {
  const [tab, setTab] = useState<Tab>("command_center");
  const [token, setToken] = useState<string>(platformToken());

  return (
    <div className="app">
      <header className="app-header">
        <h1>Hotel Front Desk Log</h1>
        <label>
          Platform token
          <input
            value={token}
            onChange={(event) => {
              setToken(event.target.value);
              setPlatformToken(event.target.value);
            }}
            aria-label={PLATFORM_TOKEN_STORAGE_KEY}
          />
        </label>
      </header>
      <nav className="tabs">
        {TABS.map((item) => (
          <button
            key={item.id}
            className={item.id === tab ? "active" : ""}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>
      <main>
        {tab === "command_center" ? <CommandCenter /> : null}
        {tab === "operational_chat" ? <OperationalChat /> : null}
        {tab === "resident_engineer" ? <ResidentEngineer /> : null}
      </main>
    </div>
  );
}
