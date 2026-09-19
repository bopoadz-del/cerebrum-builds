import React, { useEffect, useState } from 'react';
import { api, Capability, setPlatformToken } from './api';
import CommandCenter from './modules/command_center';
import OperationalChat from './modules/operational_chat';
import ResidentEngineer from './modules/resident_engineer';

type Tab = 'portfolio' | 'documents' | 'status';

const TABS: { id: Tab; label: string }[] = [
  { id: 'portfolio', label: 'Portfolio and spend' },
  { id: 'documents', label: 'Ask the finance documents' },
  { id: 'status', label: 'Platform status' },
];

export default function App(): JSX.Element {
  const [tab, setTab] = useState<Tab>('portfolio');
  const [capabilities, setCapabilities] = useState<Capability[]>([]);
  const [error, setError] = useState<string>('');
  const [token, setToken] = useState<string>('');

  useEffect(() => {
    api
      .capabilities()
      .then((payload) => setCapabilities(payload.items || []))
      .catch((exc: Error) => setError(exc.message));
  }, []);

  return (
    <main className="finops-shell">
      <header>
        <h1>FinOps Central</h1>
        <p>
          Budgets, spend, approvals, variance, portfolio rollup, audit evidence and
          finance document knowledge for ~40 department budget owners, the
          controllers and the CFO.
        </p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            setPlatformToken(token);
            window.location.reload();
          }}
        >
          <input
            aria-label="platform token"
            placeholder="platform token"
            value={token}
            onChange={(event) => setToken(event.target.value)}
          />
          <button type="submit">Use token</button>
        </form>
      </header>
      <nav>
        {TABS.map((item) => (
          <button
            key={item.id}
            className={item.id === tab ? 'active' : ''}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </nav>
      {error ? <p role="alert">{error}</p> : null}
      {tab === 'portfolio' ? <CommandCenter capabilities={capabilities} /> : null}
      {tab === 'documents' ? <OperationalChat /> : null}
      {tab === 'status' ? <ResidentEngineer capabilities={capabilities} /> : null}
    </main>
  );
}
