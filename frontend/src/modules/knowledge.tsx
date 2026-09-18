// House knowledge: the front desk's own corpus, over the live RAG routes.
//
// Ingest writes one tenant-scoped corpus document (POST /v1/rag/ingest);
// the query panel ranks that same tenant's rows (POST /v1/rag/query).
// Hits come back with an excerpt and a lexical score, so staff can see why
// a procedure surfaced instead of trusting a black box.
import { useState } from "react";

import { askHouse, ingestDocument, RAGHit } from "../api";

export default function Knowledge() {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [question, setQuestion] = useState("");
  const [hits, setHits] = useState<RAGHit[]>([]);
  const [planted, setPlanted] = useState<number | null>(null);
  const [error, setError] = useState("");

  async function ingest(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const body = await ingestDocument(text, title);
      setPlanted(body.id);
      setText("");
      setTitle("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function ask(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const body = await askHouse(question);
      setHits(body.hits || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <article className="knowledge">
      <h2>House knowledge</h2>
      <form onSubmit={ingest}>
        <input
          placeholder="document title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
        />
        <textarea
          placeholder="procedure text (late arrivals, key handling, ...)"
          value={text}
          onChange={(event) => setText(event.target.value)}
        />
        <button type="submit">Ingest</button>
      </form>
      {planted !== null ? <p>Ingested document #{planted}</p> : null}
      <form onSubmit={ask}>
        <input
          placeholder="late arrival policy?"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
        />
        <button type="submit">Query</button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      <ol>
        {hits.map((hit) => (
          <li key={hit.id}>
            {hit.title} — score {hit.score}: {hit.excerpt}
          </li>
        ))}
      </ol>
    </article>
  );
}
