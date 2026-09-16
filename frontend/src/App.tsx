/**
 * VetClinicOS console.
 *
 * Written by the factory WRITER role (codewhale exec).
 *
 * The shell binds the three declared modules to the live platform: every
 * panel talks to the booted FastAPI routes under /v1 (POST /v1/{capability}
 * to create, GET /v1/{capability} to read back, POST /v1/{capability}/{id}
 * /document to render). No second API, no mock data.
 */
import React, { useState } from "react";

import CommandCenter from "./modules/command_center";
import OperationalChat from "./modules/operational_chat";
import ResidentEngineer from "./modules/resident_engineer";

export type Session = {
  token: string;
  tenantId: string;
  roles: string[];
};

const CAPABILITIES = [
  "patient_records",
  "appointment_scheduling",
  "treatment_management",
  "billing_invoicing",
  "inventory_management",
  "audit_trail",
  "role_management",
  "clinic_analytics",
];

export default function App(): JSX.Element {
  const [token, setToken] = useState("dev-local-token");
  const [tenantId, setTenantId] = useState("local");
  const [roles, setRoles] = useState<string[]>(["admin"]);
  const session: Session = { token, tenantId, roles };

  async function connect(): Promise<void> {
    const response = await fetch("/v1/roles", {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      setRoles([]);
      return;
    }
    const body = await response.json();
    setTenantId(body?.tenant?.tenant_id ?? "local");
    setRoles(body?.tenant?.roles ?? []);
  }

  return (
    <main className="vetclinicos">
      <header>
        <h1>VetClinicOS</h1>
        <p>Practice management for vets, receptionists and admins.</p>
        <label>
          Platform token
          <input value={token} onChange={(event) => setToken(event.target.value)} />
        </label>
        <button onClick={connect}>Connect</button>
        <span data-tenant={tenantId}>tenant: {tenantId}</span>
        <span data-roles={roles.join(",")}>roles: {roles.join(", ") || "none"}</span>
      </header>

      <CommandCenter session={session} capabilities={CAPABILITIES} />
      <OperationalChat session={session} />
      <ResidentEngineer session={session} />
    </main>
  );
}
