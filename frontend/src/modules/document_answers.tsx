/**
 * Document answers: the retrieval path with its authority label.
 *
 * Wraps the same routes the chat module uses and exists for the operator who
 * wants the evidence laid out: which document each claim came from, which
 * authority layer each source belongs to (precedence.v1), and the score the
 * retrieval gave it. A refused answer shows the reason the platform named.
 */
import { useState } from "react";
import { AnswerEnvelope, askCorpus, ingestDocument } from "../api";

export default function DocumentAnswers({ token }: { token: string }) {
  const [question, setQuestion] = useState("What is the room service cut-off time?");
  const [answer, setAnswer] = useState<AnswerEnvelope | null>(null);
  const [planted, setPlanted] = useState("");

  async function plant() {
    const result = await ingestDocument(token, {
      title: "Room service SOP",
      kind: "sop",
      text: "Room service accepts orders until 23:30. After 23:30 the night auditor records a late request in the folio note.",
      authority: "documents",
    });
    setPlanted(result.body ? `document ${result.body.document_id} (${result.body.chunks} chunks)` : `HTTP ${result.status}`);
  }

  async function ask() {
    const result = await askCorpus(token, question, 3);
    setAnswer(result.body);
  }

  return (
    <section>
      <h3 style={{ fontSize: 14 }}>Document answers</h3>
      <button onClick={() => void plant()}>Plant the room service SOP</button>
      {planted && <span style={{ marginLeft: 8, opacity: 0.7 }}>{planted}</span>}
      <div>
        <input value={question} onChange={(e) => setQuestion(e.target.value)} size={50} />
        <button onClick={() => void ask()}>Answer</button>
      </div>
      {answer && (
        <div>
          <p>
            authority {answer.authority} · precedence {answer.precedence}
            {answer.refused ? ` · refused (${answer.reason})` : ""}
          </p>
          <p>{answer.answer || "no answer: no source in this corpus"}</p>
          <ol>
            {(answer.hits || []).map((hit, index) => (
              <li key={index}>
                {hit.title} [{hit.authority}] — {(hit.text || "").slice(0, 120)}
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}
