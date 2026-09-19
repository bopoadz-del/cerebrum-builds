import React, { useEffect, useState } from 'react';
import { api, Capability, setPlatformToken } from './api';
import CommandCenter from './modules/command_center';
import OperationalChat from './modules/operational_chat';
import ResidentEngineer from './modules/resident_engineer';

type Tab = 'command_center' | 'operational_chat' | 'resident_engineer';

const TABS: { id: Tab; label: string }[] = [
  { id: 'command_center', label: 'Command centre' },
  { id: 'operational_chat', label: 'Ask the documents' },
  { id: 'resident_engineer', label: 'Platform status' },
];

export default function App(): JSX.Element {
  const [tab, setTab] = useState<Tab>('command_center');
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
    <main className="bakery-shell">
      <header>
        <h1>Bakery Branch Operations Platform</h1>
        <p>Five branches, one set of books, live stock and dispatch.</p>
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
      {tab === 'command_center' ? <CommandCenter capabilities={capabilities} /> : null}
      {tab === 'operational_chat' ? <OperationalChat /> : null}
      {tab === 'resident_engineer' ? <ResidentEngineer capabilities={capabilities} /> : null}
    </main>
  );
}
