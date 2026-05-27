import { useEffect, useState } from 'react';
import { api } from './services/api';
import { ImportPage } from './pages/ImportPage';
import { ProcessingPage } from './pages/ProcessingPage';

type Screen = 'loading' | 'import' | 'processing' | 'done' | 'error';

export function App() {
  const [screen, setScreen] = useState<Screen>('loading');
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const maxAttempts = 10;
    const delayMs = 300;

    const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

    const checkBackend = async () => {
      for (let attempt = 0; attempt < maxAttempts && active; attempt += 1) {
        try {
          await api.health();
          if (active) setScreen('import');
          return;
        } catch {
          await wait(delayMs);
        }
      }
      if (active) setScreen('error');
    };

    checkBackend();
    return () => {
      active = false;
    };
  }, []);

  const handleSessionCreated = (sessionId: string) => {
    setActiveSessionId(sessionId);
    setScreen('processing');
  };

  const handleProcessingComplete = () => {
    setScreen('done');
  };

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif' }}>
      {screen === 'loading' && (
        <main style={{ padding: '2rem' }}>
          <p style={{ color: '#666' }}>Connecting to backend…</p>
        </main>
      )}
      {screen === 'error' && (
        <main style={{ padding: '2rem' }}>
          <h1>hand2notes</h1>
          <p style={{ color: '#cc0000' }}>Backend unavailable. Make sure the Python API is running.</p>
        </main>
      )}
      {screen === 'import' && (
        <ImportPage onSessionCreated={handleSessionCreated} />
      )}
      {screen === 'processing' && activeSessionId && (
        <ProcessingPage sessionId={activeSessionId} onComplete={handleProcessingComplete} />
      )}
      {screen === 'done' && (
        <main style={{ padding: '2rem' }}>
          <h1>Export complete</h1>
          <p>Your notes have been written to the Obsidian vault.</p>
          <button
            style={{ marginTop: '1rem', padding: '0.5rem 1.2rem', cursor: 'pointer' }}
            onClick={() => { setActiveSessionId(null); setScreen('import'); }}
          >
            Process another session
          </button>
        </main>
      )}
    </div>
  );
}
