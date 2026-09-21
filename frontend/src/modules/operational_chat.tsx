/**
 * Operational chat: ask the property's own documents.
 *
 * The question goes to POST /v1/rag/query, which answers from THIS tenant's
 * ingested corpus and labels the answer with the authority layer it came from
 * (certified > documents > formulas > procedures, precedence.v1). When nothing
 * in the corpus matches, the platform refuses with a named reason instead of
 * answering from memory, and the console shows that refusal as-is.
 */
import { useState } from "react";
import { AnswerEnvelope, askCorpus, ingestDocument } from "../api";

export interface OperationalChatProps {
  token: string;
}

export default function OperationalChat({ token }: OperationalChatProps) {
  const [title, setTitle] = useState("Front desk SOP");
  const [kind, setKind] = useState("sop");
  const [text, setText] = useState(
    "Late checkout policy: a guest may keep the room until 14:00 when the front desk approves it.",
  );
  const [question, setQuestion] = useState("When may a guest keep the room until 14:00?");
  const [answer, setAnswer] = useState<AnswerEnvelope | null>(null);
  const [note, setNote] = useState("");

  async function ingest() {
    const result = await ingestDocument(token, { title, kind, text });
    setNote(
      result.body
        ? `ingested ${result.body.chunks} chunk(s) as ${result.body.authority} (document ${result.body.document_id})`
        : `ingest answered ${result.status}`,
    );
  }

  async function ask() {
    const result = await askCorpus(token, question, 4);
    setAnswer(result.body);
  }

  return (
    <section style={{ marginTop: 24 }}>
      <h2 style={{ fontSize: 16 }}>Documents</h2>
      <input value={title} onChange={(e) => setTitle(e.target.value)} />
      <select value={kind} onChange={(e) => setKind(e.target.value)}>
        <option value="manual">manual</option>
        <option value="sop">sop</option>
        <option value="rate_sheet">rate sheet</option>
        <option value="policy">policy</option>
      </select>
      <button onClick={() => void ingest()}>Ingest</button>
      <textarea value={text} onChange={(e) => setText(e.target.value)} style={{ width: "100%", minHeight: 80 }} />
      <div>
        <input value={question} onChange={(e) => setQuestion(e.target.value)} size={60} />
        <button onClick={() => void ask()}>Ask</button>
      </div>
      {note && <p style={{ opacity: 0.8 }}>{note}</p>}
      {answer && (
        <div>
          <p>
            <span style={{ border: "1px solid #8883", borderRadius: 999, padding: "1px 8px" }}>
              authority: {answer.authority || "unknown"} (rank {answer.rank ?? "?"})
            </span>
            {answer.refused ? <strong> refused: {answer.reason}</strong> : null}
          </p>
          <p>{answer.answer || "(no answer — no source in this corpus)"}</p>
          <ul>
            {(answer.citations || []).map((citation, index) => (
              <li key={index}>
                {citation.title} [{citation.authority}] score {citation.score}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
