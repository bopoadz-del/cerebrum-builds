/**
 * Operational chat: ask the clinic's own corpus, with citations.
 *
 * Written by the factory WRITER role (codewhale exec).
 *
 * The question goes to POST /v1/rag/query; the answer comes back grounded in
 * the tenant's ingested corpus, with the hits that support it. When the
 * corpus has no match the panel says so instead of inventing an answer, and
 * the authority ladder (GET /v1/authority) shows which layer would win a
 * conflict.
 */
import React, { useState } from "react";

import type { Session } from "../App";

type Hit = { doc_id: string; text: string; score: number };

export default function OperationalChat(props: { session: Session }): JSX.Element {
  const { session } = props;
  const [question, setQuestion] = useState("vaccination schedule for puppies");
  const [answer, setAnswer] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [ladder, setLadder] = useState<string>("");

  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${session.token}`,
  };

  async function ask(): Promise<void> {
    const response = await fetch("/v1/rag/query", {
      method: "POST",
      headers,
      body: JSON.stringify({ query: question, top_k: 5 }),
    });
    const body = await response.json();
    setAnswer(body.grounded ? body.answer : "no corpus match — ingest a document first");
    setHits(body.hits ?? []);
    const authority = await fetch("/v1/authority", { headers });
    const authorityBody = await authority.json();
    setLadder((authorityBody.layers ?? []).map((layer: { id: string }) => layer.id).join(" > "));
  }

  async function ingest(): Promise<void> {
    await fetch("/v1/rag/ingest", {
      method: "POST",
      headers,
      body: JSON.stringify({ text: question, collection: "clinic_corpus" }),
    });
    await ask();
  }

  return (
    <section data-module="operational_chat">
      <h2>Ask the clinic</h2>
      <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
      <button onClick={() => void ask()}>Ask</button>
      <button onClick={() => void ingest()}>Ingest as document</button>
      <p data-grounded={hits.length > 0}>
        Answer: {answer} {answer ? <small>— extractive, cited below</small> : null}
      </p>
      <p data-authority>{ladder}</p>
      <ul>
        {hits.map((hit) => (
          <li key={hit.doc_id}>
            <strong>{hit.doc_id}</strong> ({hit.score}) {hit.text.slice(0, 160)}
          </li>
        ))}
      </ul>
    </section>
  );
}
