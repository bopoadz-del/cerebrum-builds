import React, { useState } from 'react';
import { api } from '../api';

/**
 * Ask the platform's own finance documents.
 *
 * Posts the question to POST /v1/rag/query, which retrieves from the caller's
 * tenant-scoped index and answers from the passages it found. The answer is
 * shown with its citations; when the corpus has nothing to say, the platform
 * says so rather than inventing a figure.
 */
export default function OperationalChat() {
  const [question, setQuestion] = useState<string>(
    'What is the invoice approval threshold?',
  );
  const [answer, setAnswer] = useState<string>('');
  const [citations, setCitations] = useState<string[]>([]);
  const [passage, setPassage] = useState<string>('');
  const [documentType, setDocumentType] = useState<string>('policy');
  const [busy, setBusy] = useState<boolean>(false);

  async function ask(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const payload = await api.ask(question);
      setAnswer(String(payload.answer || ''));
      setCitations((payload.citations || []).map((citation) => JSON.stringify(citation)));
    } catch (exc) {
      setAnswer((exc as Error).message);
      setCitations([]);
    } finally {
      setBusy(false);
    }
  }

  async function index(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api.ingest(passage, documentType);
      setAnswer('Passage indexed. Ask a question that mentions it.');
    } catch (exc) {
      setAnswer((exc as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="document-knowledge">
      <h2>Ask the invoices, contracts, policies and price lists</h2>
      <form onSubmit={ask}>
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} />
        <button type="submit" disabled={busy}>
          POST /v1/rag/query
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
      <form onSubmit={index}>
        <textarea
          aria-label="document passage"
          placeholder="paste a passage from an invoice, contract, policy or price list"
          value={passage}
          onChange={(event) => setPassage(event.target.value)}
        />
        <select value={documentType} onChange={(event) => setDocumentType(event.target.value)}>
          <option value="invoice">invoice</option>
          <option value="contract">contract</option>
          <option value="policy">policy</option>
          <option value="price_list">price list</option>
        </select>
        <button type="submit" disabled={busy}>
          POST /v1/rag/ingest
        </button>
      </form>
    </section>
  );
}
