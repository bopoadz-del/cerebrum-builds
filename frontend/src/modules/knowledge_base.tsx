/* Knowledge base: the job's own documents, retrievable offline.
 *
 * Talks to the live retrieval surface only — POST /v1/rag/ingest and
 * POST /v1/rag/query (app/rag_routes.py). The tenant is resolved from the
 * bearer token on the server, never sent from here, so this panel cannot
 * ask for another practice's corpus.
 */

import { useCallback, useState } from "react";

import { authHeaders } from "../App";

interface Hit {
  id: number;
  source?: string;
  ordinal?: number;
  score?: number;
  matched_terms?: number;
  text?: string;
}

export default function KnowledgeBaseModule() {
  const [document, setDocument] = useState("");
  const [source, setSource] = useState("job-protocol");
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [status, setStatus] = useState("idle");

  const ingest = useCallback(async () => {
    if (!document.trim()) {
      setStatus("nothing to ingest");
      return;
    }
    setStatus("ingesting");
    const resp = await fetch("/v1/rag/ingest", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ text: document, source }),
    });
    const body = await resp.json().catch(() => ({}));
    if (!resp.ok || body?.ok === false) {
      setStatus(String(body?.detail || body?.error || resp.status));
      return;
    }
    setStatus(`indexed ${body?.ingested ?? 0} chunk(s)`);
  }, [document, source]);

  const search = useCallback(async () => {
    setStatus("searching");
    const resp = await fetch("/v1/rag/query", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ q: query, k: 5 }),
    });
    const body = await resp.json().catch(() => ({}));
    if (!resp.ok || body?.ok === false) {
      setStatus(String(body?.detail || body?.error || resp.status));
      setHits([]);
      return;
    }
    const found = (body?.hits as Hit[]) || [];
    setHits(found);
    setStatus(found.length ? `${found.length} hit(s), lexical index` : "no match");
  }, [query]);

  return (
    <section data-module="knowledge_base">
      <h2>Knowledge base</h2>
      <p>
        Local keyword index over job documents. Ingested text is stored in this
        practice&apos;s own database and is never sent anywhere.
      </p>
      <label>
        source
        <input value={source} onChange={(event) => setSource(event.target.value)} />
      </label>
      <textarea
        rows={6}
        value={document}
        placeholder="Paste a protocol, SOP or discharge instruction"
        onChange={(event) => setDocument(event.target.value)}
      />
      <button type="button" onClick={ingest}>
        ingest
      </button>
      <label>
        query
        <input value={query} onChange={(event) => setQuery(event.target.value)} />
      </label>
      <button type="button" onClick={search}>
        search
      </button>
      <p role="status">{status}</p>
      <ul>
        {hits.map((hit) => (
          <li key={hit.id}>
            <strong>{hit.source || "inline"}</strong> #{hit.ordinal} (score {hit.score})
            <p>{hit.text}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
