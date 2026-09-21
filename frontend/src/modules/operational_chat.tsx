import { useState } from "react";
import { Api, type Authority } from "../api";
import { layerBadge } from "../App";

type Turn = { you: string; say: string; withheld: boolean; outcome: string | null; authority?: Authority };

const CALL_SID = "CAmc000000000000000000000000001";

export function OperationalChat(props: { api: Api; campaign: string }) {
  const { api } = props;
  const [project, setProject] = useState("az-zahra");
  const [outcome, setOutcome] = useState("project_interested");
  const [text, setText] = useState("I like this project, what is the payment plan and when is handover?");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);

  const send = async () => {
    const gathered = await api.ask(text, project, "en");
    const payload = gathered.payload as unknown as { say?: string; withheld?: boolean; outcome?: string | null };
    setTurns((current) => [
      ...current,
      {
        you: text,
        say: String(payload.say ?? ""),
        withheld: Boolean(payload.withheld),
        outcome: payload.outcome ?? null,
        authority: gathered.payload.authority,
      },
    ]);
  };

  const qualify = async () => {
    const result = await api.qualify(CALL_SID, outcome, text, project);
    setSummary(result.payload as unknown as Record<string, unknown>);
  };

  const transfer = async () => {
    const result = await api.transfer(CALL_SID, outcome, project);
    setSummary(result.payload as unknown as Record<string, unknown>);
  };

  return (
    <section className="card">
      <h2>Operational chat — the dialogue and the handover</h2>
      <div className="row">
        <label>
          Project tag
          <input value={project} onChange={(event) => setProject(event.target.value)} />
        </label>
        <label>
          Outcome
          <select value={outcome} onChange={(event) => setOutcome(event.target.value)}>
            <option>project_interested</option>
            <option>other_re_interested</option>
            <option>not_interested</option>
          </select>
        </label>
      </div>
      <label htmlFor="said">What the caller said</label>
      <textarea id="said" value={text} onChange={(event) => setText(event.target.value)} />
      <div className="row">
        <button onClick={() => void send()}>Speak</button>
        <button onClick={() => void qualify()}>Qualify</button>
        <button onClick={() => void transfer()}>Warm transfer</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>Caller</th>
            <th>Agent</th>
            <th>Outcome</th>
          </tr>
        </thead>
        <tbody>
          {turns.map((turn, index) => (
            <tr key={index}>
              <td>{turn.you}</td>
              <td>
                {turn.say} {turn.withheld ? <em className="dim">(withheld)</em> : null}
                {layerBadge(turn.authority)}
              </td>
              <td>{turn.outcome ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {summary ? <pre>{JSON.stringify(summary, null, 1)}</pre> : null}
    </section>
  );
}
