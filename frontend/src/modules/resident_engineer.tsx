/* Generated UI module: resident_engineer — RetailOS operating surface. */
import { useCallback, useEffect, useState } from "react";

const MODULE_ID = "resident_engineer";
const PRODUCT_ID = "retail";
const CAPABILITIES = ['customer_insights', 'analytics_dashboard', 'compliance_and_audit'];

type Row = { id?: number; reference?: string; status?: string };

export default function ResidentEngineerModule() {
  const [health, setHealth] = useState<string>("pending");
  const [rows, setRows] = useState<Record<string, Row[]>>({});
  const [error, setError] = useState<string>("");

  useEffect(() => {
    fetch("/health")
      .then((r) => (r.ok ? "ok" : "degraded"))
      .catch(() => "unreachable")
      .then(setHealth);
  }, []);

  const load = useCallback(async (capability: string) => {
    try {
      const resp = await fetch("/v1/" + capability);
      const body = await resp.json();
      const items = Array.isArray(body) ? body : body.items || [];
      setRows((current) => ({ ...current, [capability]: items }));
    } catch (exc) {
      setError(String(exc));
    }
  }, []);

  useEffect(() => {
    load("compliance_and_audit");
  }, [load]);

  return (
    <section data-module={MODULE_ID} data-product={PRODUCT_ID}>
      <header>
        <h2>{MODULE_ID}</h2>
        <p>Runtime health: {health}</p>
        {error ? <p role="alert">{error}</p> : null}
      </header>
      <ul>
        {CAPABILITIES.map((id) => (
          <li key={id} data-capability={id}>
            <button type="button" onClick={() => load(id)}>
              {id}
            </button>
            <span data-rows={id}>{(rows[id] || []).length}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
