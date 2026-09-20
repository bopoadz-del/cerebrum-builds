/**
 * Operational chat: ask the platform about the estate it holds.
 *
 * Written by the factory WRITER role (codewhale exec)
 *
 * The answer is composed offline from the platform's own records and carries
 * the authority layer it came from; the screen never invents text when the
 * platform has nothing to quote.
 */

import React, { useCallback, useState } from "react";
import { authorityLadder, listRecords, type Envelope } from "../api";

export default function OperationalChat(props: { capabilities: string[] }): JSX.Element {
  const [question, setQuestion] = useState<string>("");
  const [answer, setAnswer] = useState<Envelope | null>(null);
  const [ladder, setLadder] = useState<Envelope | null>(null);

  const ask = useCallback(async (): Promise<void> => {
    const held = await listRecords(props.capabilities[0] ?? "complaints_management");
    const items = (held.items as Array<Record<string, unknown>> | undefined) ?? [];
    const terms = question
      .toLowerCase()
      .split(/\s+/)
      .filter((term) => term.length > 2);
    const matches = items.filter((row) =>
      terms.some((term) => JSON.stringify(row).toLowerCase().includes(term)),
    );
    setAnswer({
      ok: true,
      question,
      matched: matches.length,
      held: items.length,
      answer: matches.length
        ? `The estate holds ${matches.length} record(s) matching that question.`
        : "No record the platform holds covers that question yet.",
      citations: matches.slice(0, 3).map((row) => ({
        reference: row.reference,
        school: row.school,
      })),
    });
    setLadder(await authorityLadder());
  }, [question, props.capabilities]);

  return (
    <section className="card">
      <strong>Operational chat</strong>
      <p className="dim">
        Answers are composed from the records this platform stores, and carry
        the layer they came from.
      </p>
      <div className="row">
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="which school has the most electrical complaints?"
        />
        <button type="button" onClick={() => void ask()}>
          Ask
        </button>
      </div>
      {ladder ? (
        <span className="dim">authority {String(ladder.version)}</span>
      ) : null}
      <pre>{answer ? JSON.stringify(answer, null, 2) : "—"}</pre>
    </section>
  );
}
