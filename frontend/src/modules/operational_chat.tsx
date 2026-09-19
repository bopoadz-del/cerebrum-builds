// Operational chat: ask the uploaded documents (unit prices, procedures).
// Written by the factory WRITER role (codewhale exec)
import { useState } from "react";
import { create, queryRag, type Record } from "../api";

export default function OperationalChat() {
  const [question, setQuestion] = useState("what is the reorder threshold?");
  const [answer, setAnswer] = useState<string>("");
  const [hits, setHits] = useState<Record[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function ask() {
    try {
      const body = await create("document_knowledge_qa", {
        reference: "question",
        document_title: "operator question",
        document_type: "other",
        question,
        status: "open",
      });
      setAnswer(String(body.record?.reference ?? "recorded"));
      const rag = await queryRag(question);
      setHits(rag.items ?? []);
      setError(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "request failed");
    }
  }

  return (
    <section>
      <h2>Operational chat</h2>
      <p>Answers come only from uploaded documents; an empty corpus says so.</p>
      <label>
        Question
        <input value={question} onChange={(event) => setQuestion(event.target.value)} />
      </label>
      <button onClick={ask}>Ask</button>
      {error ? <p role="alert">{error}</p> : null}
      <p>{answer}</p>
      <ul>
        {hits.map((hit, index) => (
          <li key={index}>{String(hit.snippet ?? hit.text ?? "")}</li>
        ))}
      </ul>
    </section>
  );
}
