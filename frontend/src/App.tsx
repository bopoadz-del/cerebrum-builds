// Bakery Chain Operations & Delivery Platform operator console: one screen per capability, all over the live routes.
// Written by the factory WRITER role (codewhale exec)
import { useEffect, useState } from "react";
import { CAPABILITIES, CapabilityId, list, health, type Record } from "./api";
import CommandCenter from "./modules/command_center";
import OperationalChat from "./modules/operational_chat";
import ResidentEngineer from "./modules/resident_engineer";
import StockInventoryManagement from "./modules/stock_inventory_management";
import ProductPricing from "./modules/product_pricing";
import DeliveryDispatchTracking from "./modules/delivery_dispatch_tracking";
import FleetCostTracking from "./modules/fleet_cost_tracking";
import ManagementReportingDashboard from "./modules/management_reporting_dashboard";
import UserRolesWorkforce from "./modules/user_roles_workforce";
import DocumentKnowledgeQa from "./modules/document_knowledge_qa";
import ProceduresReadinessAndAuditTrail from "./modules/procedures_readiness_and_audit_trail";

const MODULES: globalThis.Record<CapabilityId, (props: { capability: CapabilityId }) => JSX.Element> = {
  stock_inventory_management: StockInventoryManagement,
  product_pricing: ProductPricing,
  delivery_dispatch_tracking: DeliveryDispatchTracking,
  fleet_cost_tracking: FleetCostTracking,
  management_reporting_dashboard: ManagementReportingDashboard,
  user_roles_workforce: UserRolesWorkforce,
  document_knowledge_qa: DocumentKnowledgeQa,
  procedures_readiness_and_audit_trail: ProceduresReadinessAndAuditTrail,
};

const VIEWS = ["command_center", "operational_chat", "resident_engineer"] as const;
type View = (typeof VIEWS)[number] | CapabilityId;

export default function App() {
  const [active, setActive] = useState<View>("command_center");
  const [status, setStatus] = useState("checking");
  const [rows, setRows] = useState<Record[]>([]);

  useEffect(() => {
    health().then((body) => setStatus(body.status)).catch(() => setStatus("degraded"));
  }, []);

  const capabilityView = (CAPABILITIES as readonly string[]).includes(active);
  const Module = capabilityView
    ? MODULES[active as CapabilityId]
    : null;

  useEffect(() => {
    if (!capabilityView) {
      setRows([]);
      return;
    }
    list(active as CapabilityId)
      .then((body) => setRows(body.items ?? []))
      .catch(() => setRows([]));
  }, [active, capabilityView]);

  return (
    <main>
      <header>
        <h1>Bakery Chain Operations & Delivery Platform</h1>
        <p>Chain status: {status}</p>
      </header>
      <nav>
        {VIEWS.map((view) => (
          <button key={view} onClick={() => setActive(view)}>
            {view.replace(/_/g, " ")}
          </button>
        ))}
        {CAPABILITIES.map((capability) => (
          <button key={capability} onClick={() => setActive(capability)}>
            {capability.replace(/_/g, " ")}
          </button>
        ))}
      </nav>
      {active === "command_center" ? <CommandCenter /> : null}
      {active === "operational_chat" ? <OperationalChat /> : null}
      {active === "resident_engineer" ? <ResidentEngineer /> : null}
      {Module ? <Module capability={active as CapabilityId} /> : null}
      {capabilityView ? (
        <section>
          <h2>{active.replace(/_/g, " ")}</h2>
          <p>{rows.length} persisted record(s)</p>
          <table>
            <tbody>
              {rows.map((row) => (
                <tr key={String(row.id)}>
                  <td>{row.id}</td>
                  <td>{row.reference}</td>
                  <td>{row.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ) : null}
    </main>
  );
}
