// Operational chat: ask the house questions, answered offline with labels.
import { useState } from "react";

type Answer = {
  answer: string;
  winner: { layer: string; source: string } | null;
  labels: { layer: string; rank: number }[];
  divergence: { source: string; reason: string }[];
};

export default function OperationalChat() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [error, setError] = useState("");

  async function ask(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const response = await fetch(`/v1/answers?q=${encodeURIComponent(question)}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("front-desk-token") || ""}` },
      });
      const body = await response.json();
      if (body.ok === false) throw new Error(String(body.error));
      setAnswer(body as Answer);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <article className="operational-chat">
      <h2>Operational chat</h2>
      <form onSubmit={ask}>
        <input
          placeholder="late arrival policy?"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
        />
        <button type="submit">Ask</button>
      </form>
      {error ? <p className="error">{error}</p> : null}
      {answer ? (
        <div>
          <p>{answer.answer}</p>
          <p>
            Winner: {answer.winner ? `${answer.winner.layer} · ${answer.winner.source}` : "none"}
          </p>
          <ul>
            {answer.labels.map((label) => (
              <li key={`${label.layer}-${label.rank}`}>
                layer {label.rank}: {label.layer}
              </li>
            ))}
          </ul>
          {answer.divergence.length ? (
            <details>
              <summary>{answer.divergence.length} divergence record(s)</summary>
              <ul>
                {answer.divergence.map((record) => (
                  <li key={record.source}>{record.reason}</li>
                ))}
              </ul>
            </details>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
