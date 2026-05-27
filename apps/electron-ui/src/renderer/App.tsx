import { useEffect, useState } from 'react';
import { api } from './services/api';

// Foundation smoke-test shell: confirms the renderer can reach the spawned
// Python backend. Feature screens (Import/Processing/Review/Export/Settings)
// are added in their respective user-story phases.
export function App() {
  const [status, setStatus] = useState<'connecting' | 'ok' | 'error'>('connecting');

  useEffect(() => {
    api
      .health()
      .then(() => setStatus('ok'))
      .catch(() => setStatus('error'));
  }, []);

  return (
    <main style={{ fontFamily: 'system-ui, sans-serif', padding: '2rem' }}>
      <h1>hand2notes</h1>
      <p>
        Backend:{' '}
        <strong>
          {status === 'connecting' && 'connecting…'}
          {status === 'ok' && 'connected'}
          {status === 'error' && 'unavailable'}
        </strong>
      </p>
    </main>
  );
}
