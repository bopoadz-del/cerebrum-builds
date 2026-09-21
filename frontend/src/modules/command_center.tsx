import { useState } from "react";
import { Api, type Capability, type Authority } from "../api";
import { layerBadge } from "../App";

type Answer = { status: number; ok: boolean; payload: Record<string, unknown> };

const SHEET = [
  "Az Zahra Tower price list.",
  "",
  "One bedroom apartments start from AED 1,250,000. Two bedroom from AED 1,890,000.",
  "",
  "Payment plan: 20% down payment and 60 monthly instalments. Handover Q4 2027.",
].join("\n");

const LEADS = ["name,phone,language,project", "Fatima Al Ali,+971501234567,ar,az-zahra", "Omar Haddad,+971509876543,en,marina-gate"].join("\n");

export function CommandCenter(props: { api: Api; campaign: string; capabilities: Capability[] }) {
  const { api, campaign } = props;
  const [leads, setLeads] = useState(LEADS);
  const [sheet, setSheet] = useState(SHEET);
  const [project, setProject] = useState("az-zahra");
  const [question, setQuestion] = useState("What is the starting price and when is handover?");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [queue, setQueue] = useState<Answer | null>(null);
  const [metrics, setMetrics] = useState<Answer | null>(null);

  const show = async (promise: Promise<Answer>) => {
    const result = (await promise) as unknown as Answer;
    setAnswer(result);
    return result;
  };

  return (
    <section className="grid">
      <div className="card">
        <h2>Lead file → dial queue</h2>
        <label htmlFor="leads">Brokerage lead file (CSV)</label>
        <textarea id="leads" value={leads} onChange={(event) => setLeads(event.target.value)} />
        <div className="row">
          <button onClick={() => void show(api.importLeads(leads, campaign, project))}>Parse &amp; queue</button>
          <button onClick={() => void show(api.dialQueue(campaign).then((r) => { setQueue(r); return r; }))}>
            Show dial queue
          </button>
        </div>
        {queue ? (
          <div className="dim">
            calls remaining {String((queue.payload.cap as { result: number } | undefined)?.result ?? "—")}
            {layerBadge(queue.payload.authority as Authority | undefined)} · depth {JSON.stringify(queue.payload.depth)}
          </div>
        ) : null}
      </div>

      <div className="card">
        <h2>Project sheet → grounded pitch</h2>
        <label htmlFor="sheet">Project sheet (price list, payment plan, handover)</label>
        <textarea id="sheet" value={sheet} onChange={(event) => setSheet(event.target.value)} />
        <div className="row">
          <label>
            Project tag
            <input value={project} onChange={(event) => setProject(event.target.value)} />
          </label>
          <button onClick={() => void show(api.ingest(sheet, project))}>Ingest</button>
        </div>
        <label htmlFor="question">Caller&apos;s question</label>
        <input id="question" value={question} onChange={(event) => setQuestion(event.target.value)} />
        <div className="row">
          <button onClick={() => void show(api.ground(project, question))}>Ask (cite or refuse)</button>
        </div>
      </div>

      <div className="card">
        <h2>Campaign metrics (formulas)</h2>
        <div className="row">
          <button onClick={() => void show(api.dashboard(campaign).then((r) => { setMetrics(r); return r; }))}>
            Load dashboard
          </button>
          <button onClick={() => void show(api.runFormula("calls_remaining", { daily_cap: 250, attempted_today: 40 }))}>
            calls_remaining
          </button>
          <button onClick={() => void show(api.runFormula("price_with_tax", { amount: 1250000, quantity: 1 }))}>
            price_with_tax
          </button>
        </div>
        {metrics ? <div dangerouslySetInnerHTML={{ __html: String(metrics.payload.chart ?? "") }} /> : null}
      </div>

      <div className="card">
        <h2>Answer</h2>
        <pre>{answer ? `${answer.status}\n` + JSON.stringify(answer.payload, null, 1) : "—"}</pre>
        {answer ? layerBadge(answer.payload.authority as Authority | undefined) : null}
      </div>
    </section>
  );
}
