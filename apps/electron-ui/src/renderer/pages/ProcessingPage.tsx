import { useEffect, useRef } from 'react';
import { api } from '../services/api';
import { usePipelineStore } from '../stores/pipelineStore';

const STAGE_LABELS: Record<string, string> = {
  import: 'Importing images',
  preprocess: 'Preprocessing (deskew & denoise)',
  detect_layout: 'Detecting layout regions',
  recognize_text: 'Recognizing text (OCR)',
  reconstruct_structure: 'Reconstructing structure',
  generate_output: 'Generating Markdown output',
};

interface Props {
  sessionId: string;
  onComplete: () => void;
}

export function ProcessingPage({ sessionId, onComplete }: Props) {
  const {
    runId,
    stages,
    progressPercent,
    isRunning,
    isCancelling,
    error,
    startRun,
    setStageStarted,
    setStageCompleted,
    setError,
    requestCancel,
    finishRun,
  } = usePipelineStore();

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;

    const start = async () => {
      try {
        const resp = await api.startProcessing(sessionId);
        if (cancelled) return;
        startRun(resp.run_id, sessionId);

        const ws = api.openProgressSocket(sessionId);
        wsRef.current = ws;

        ws.onmessage = (evt) => {
          const event = JSON.parse(evt.data as string);
          switch (event.event) {
            case 'stage_started':
              setStageStarted(event.stage);
              break;
            case 'stage_completed':
              setStageCompleted(event.stage, event.metrics ?? {});
              break;
            case 'run_completed':
              finishRun();
              ws.close();
              onComplete();
              break;
            case 'run_failed':
              setError(event.error ?? 'Pipeline failed');
              ws.close();
              break;
            case 'run_cancelled':
              finishRun();
              ws.close();
              break;
          }
        };
        ws.onerror = () => setError('WebSocket connection lost');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to start pipeline');
      }
    };

    void start();
    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, [sessionId]);

  const handleCancel = async () => {
    if (!runId) return;
    requestCancel();
    try {
      await api.cancelRun(sessionId, runId);
    } catch {
      /* ignore */
    }
  };

  return (
    <main style={{ padding: '2rem', maxWidth: 560 }}>
      <h1>Processing</h1>

      <div style={{ marginBottom: '1.5rem' }}>
        <div style={{ background: '#e8e8e8', borderRadius: 8, height: 12, overflow: 'hidden' }}>
          <div
            style={{
              background: error ? '#cc0000' : '#0066cc',
              height: '100%',
              width: `${progressPercent}%`,
              transition: 'width 0.4s ease',
            }}
          />
        </div>
        <p style={{ fontSize: '0.875rem', color: '#666', marginTop: '0.4rem' }}>{progressPercent}%</p>
      </div>

      <ul style={{ listStyle: 'none', padding: 0 }}>
        {stages.map((st) => (
          <li key={st.stage} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.6rem' }}>
            <StageIcon status={st.status} />
            <span style={{ fontSize: '0.9rem', color: st.status === 'idle' ? '#aaa' : '#222' }}>
              {STAGE_LABELS[st.stage] ?? st.stage}
            </span>
          </li>
        ))}
      </ul>

      {error && <p style={{ color: '#cc0000', marginTop: '1rem' }}>{error}</p>}

      {isRunning && !isCancelling && (
        <button onClick={handleCancel} style={cancelBtnStyle}>
          Cancel
        </button>
      )}
      {isCancelling && <p style={{ color: '#888', fontSize: '0.875rem' }}>Cancelling…</p>}
    </main>
  );
}

function StageIcon({ status }: { status: string }) {
  const icons: Record<string, string> = {
    idle: '○',
    running: '◌',
    completed: '●',
    failed: '✕',
    cancelled: '—',
  };
  const colors: Record<string, string> = {
    idle: '#ccc',
    running: '#0066cc',
    completed: '#007744',
    failed: '#cc0000',
    cancelled: '#888',
  };
  return (
    <span style={{ color: colors[status] ?? '#ccc', fontSize: '1rem', width: 18, textAlign: 'center' }}>
      {icons[status] ?? '○'}
    </span>
  );
}

const cancelBtnStyle: React.CSSProperties = {
  marginTop: '1.5rem',
  padding: '0.5rem 1.2rem',
  background: '#fff',
  border: '1px solid #ccc',
  borderRadius: 6,
  cursor: 'pointer',
  fontSize: '0.875rem',
};
