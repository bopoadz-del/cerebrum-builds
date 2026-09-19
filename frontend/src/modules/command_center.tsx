import React, { useEffect, useMemo, useState } from 'react';
import { api, Capability, PlatformRecord } from '../api';

/**
 * Command centre: department budgets, spend and the consolidated rollup.
 *
 * Every row comes from the live route: GET /v1/<capability> for the selected
 * capability, and the budget line is created through
 * POST /v1/budget_planning_tracking. The client never invents figures — a
 * capability with no stored records shows an empty table and says so.
 */

const MONEY_FIELDS = [
  'planned_amount',
  'actual_amount',
  'amount',
  'budget_amount',
  'spend_total',
  'commitment_total',
  'forecast_total',
];

const BUDGET_DRAFT: PlatformRecord = {
  reference: '',
  status: 'open',
  department: 'Operations',
  budget_owner: 'Budget Owner',
  cost_centre: 'CC-100',
  period: 'FY2026',
  planned_amount: 100000,
  actual_amount: 25000,
  currency: 'GBP',
  notes: 'raised from the console',
};

export default function CommandCenter({ capabilities }: { capabilities: Capability[] }) {
  const [selected, setSelected] = useState<string>('');
  const [records, setRecords] = useState<PlatformRecord[]>([]);
  const [status, setStatus] = useState<string>('');
  const [draft, setDraft] = useState<PlatformRecord>({ ...BUDGET_DRAFT });
  const [created, setCreated] = useState<string>('');

  const active = selected || capabilities[0]?.id || '';

  useEffect(() => {
    if (!active) return;
    api
      .list(active)
      .then((payload) => {
        setRecords(payload.items || []);
        setStatus(`${payload.items?.length ?? 0} stored record(s) in ${active}`);
      })
      .catch((exc: Error) => setStatus(exc.message));
  }, [active]);

  const columnNames = useMemo(() => {
    const seen: string[] = [];
    for (const record of records) {
      for (const key of Object.keys(record)) {
        if (!seen.includes(key)) seen.push(key);
      }
    }
    return seen.slice(0, 8);
  }, [records]);

  async function raiseBudgetLine(event: React.FormEvent) {
    event.preventDefault();
    try {
      const payload = await api.create('budget_planning_tracking', {
        ...draft,
        reference: `console-${Date.now()}`,
      });
      setCreated(JSON.stringify(payload.stored));
      if (active === 'budget_planning_tracking') {
        const listed = await api.list('budget_planning_tracking');
        setRecords(listed.items || []);
      }
    } catch (exc) {
      setCreated((exc as Error).message);
    }
  }

  return (
    <section className="portfolio-dashboard">
      <h2>Department budgets, spend and the consolidated rollup</h2>
      <label>
        Capability
        <select value={active} onChange={(event) => setSelected(event.target.value)}>
          {capabilities.map((capability) => (
            <option key={capability.id} value={capability.id}>
              {capability.id}
            </option>
          ))}
        </select>
      </label>
      <p>{status}</p>
      <table>
        <thead>
          <tr>
            {columnNames.map((name) => (
              <th key={name}>{name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {records.map((record) => (
            <tr key={String(record.id)}>
              {columnNames.map((name) => (
                <td key={name}>
                  {MONEY_FIELDS.includes(name) && typeof record[name] === 'number'
                    ? Number(record[name]).toFixed(2)
                    : String(record[name] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <form onSubmit={raiseBudgetLine}>
        <h3>Capture a budget line</h3>
        <label>
          Department
          <input
            value={String(draft.department ?? '')}
            onChange={(event) => setDraft({ ...draft, department: event.target.value })}
          />
        </label>
        <label>
          Planned amount
          <input
            type="number"
            value={Number(draft.planned_amount ?? 0)}
            onChange={(event) =>
              setDraft({ ...draft, planned_amount: Number(event.target.value) })
            }
          />
        </label>
        <label>
          Actual amount
          <input
            type="number"
            value={Number(draft.actual_amount ?? 0)}
            onChange={(event) =>
              setDraft({ ...draft, actual_amount: Number(event.target.value) })
            }
          />
        </label>
        <button type="submit">POST /v1/budget_planning_tracking</button>
      </form>
      {created ? <pre>{created}</pre> : null}
    </section>
  );
}
