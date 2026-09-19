import React, { useState } from 'react';
import { api } from '../api';

/**
 * Ask the bakery's own documents.
 *
 * Posts the question to POST /v1/rag/query, which retrieves from the caller's
 * tenant-scoped index and answers from the passages it found. The answer is
 * displayed with its citations; when the platform has nothing, it says so.
 */
export default function OperationalChat() {
  const [question, setQuestion] = useState<string>('What is the reorder threshold procedure?');
  const [answer, setAnswer] = useState<string>('');
  const [citations, setCitations] = useState<string[]>([]);
  const [passage, setPassage] = useState<string>('');
  const [busy, setBusy] = useState<boolean>(false);

  async function ask(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const payload = await api.ask(question);
      setAnswer(String(payload.answer || ''));
      setCitations(
        (payload.citations || []).map((citation) => JSON.stringify(citation)),
      );
    } catch (exc) {
      setAnswer((exc as Error).message);
      setCitations([]);
    } finally {
      setBusy(false);
    }
  }

  async function upload(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api.ingest(passage, 'price_list');
      setAnswer('Passage indexed. Ask a question that mentions it.');
    } catch (exc) {
      setAnswer((exc as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="operational-chat">
      <h2>Ask the price lists, recipes, zones and procedures</h2>
      <form onSubmit={ask}>
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
        <button type="submit" disabled={busy}>
          Ask
        </button>
      </form>
      <article>
        <h3>Answer</h3>
        <p>{answer}</p>
        <ul>
          {citations.map((citation) => (
            <li key={citation}>{citation}</li>
          ))}
        </ul>
      </article>
      <form onSubmit={upload}>
        <textarea
          aria-label="document passage"
          placeholder="paste a passage from a price list, recipe or procedure"
          value={passage}
          onChange={(event) => setPassage(event.target.value)}
        />
        <button type="submit" disabled={busy}>
          Index passage
        </button>
      </form>
    </section>
  );
}
