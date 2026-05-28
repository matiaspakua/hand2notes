import { useEffect, useRef, useState } from 'react';
import { api, connectProgress, getPageImageUrl } from '../services/api';
import type { ProgressEvent } from '../services/types';
import { usePipelineStore, type BlockOverlay } from '../stores/pipelineStore';

// ─── Block type colours (translucent fills + solid border) ───────────────────
const BLOCK_COLORS: Record<string, { fill: string; stroke: string; label: string }> = {
  title:          { fill: 'rgba(155,89,182,0.30)',  stroke: 'rgba(155,89,182,0.85)',  label: 'Title' },
  heading:        { fill: 'rgba(52,152,219,0.30)',  stroke: 'rgba(52,152,219,0.85)',  label: 'Heading' },
  paragraph:      { fill: 'rgba(46,204,113,0.22)',  stroke: 'rgba(46,204,113,0.80)',  label: 'Paragraph' },
  bullet_list:    { fill: 'rgba(26,188,156,0.28)',  stroke: 'rgba(26,188,156,0.85)',  label: 'List' },
  numbered_list:  { fill: 'rgba(22,160,133,0.28)',  stroke: 'rgba(22,160,133,0.85)',  label: 'Numbered List' },
  table:          { fill: 'rgba(230,126,34,0.35)',  stroke: 'rgba(230,126,34,0.90)',  label: 'Table' },
  diagram:        { fill: 'rgba(231,76,60,0.35)',   stroke: 'rgba(231,76,60,0.90)',   label: 'Diagram' },
  formula:        { fill: 'rgba(243,156,18,0.35)',  stroke: 'rgba(243,156,18,0.90)',  label: 'Formula' },
  callout:        { fill: 'rgba(233,30,99,0.28)',   stroke: 'rgba(233,30,99,0.85)',   label: 'Callout' },
  marginal_note:  { fill: 'rgba(149,165,166,0.28)', stroke: 'rgba(149,165,166,0.80)', label: 'Note' },
  url_reference:  { fill: 'rgba(0,188,212,0.30)',   stroke: 'rgba(0,188,212,0.85)',   label: 'URL' },
  embedded_image: { fill: 'rgba(255,87,34,0.28)',   stroke: 'rgba(255,87,34,0.85)',   label: 'Image' },
  arrow_connector:{ fill: 'rgba(96,125,139,0.25)',  stroke: 'rgba(96,125,139,0.80)',  label: 'Arrow' },
};

const FALLBACK_COLOR = { fill: 'rgba(120,120,120,0.25)', stroke: 'rgba(120,120,120,0.75)', label: 'Block' };

const STAGE_LABELS: Record<string, string> = {
  import:                'Importing images',
  preprocess:            'Preprocessing (deskew & denoise)',
  detect_layout:         'Detecting layout regions',
  recognize_text:        'Recognizing text (OCR)',
  text_correction:       'Correcting text (ES/EN dictionary)',
  reconstruct_structure: 'Reconstructing structure',
  detect_diagrams:       'Interpreting diagrams (VLM)',
  generate_output:       'Generating Markdown output',
};

interface Props {
  sessionId: string;
  onComplete: () => void;
}

export function ProcessingPage({ sessionId, onComplete }: Props) {
  const {
    runId, stages, progressPercent, isRunning, isCancelling, error,
    currentPageId, currentPageIndex, totalPages,
    currentPageWidth, currentPageHeight, currentPageBlocks,
    startRun, setStageStarted, setStageCompleted, setStageError, setError,
    requestCancel, finishRun, setPageLayout,
  } = usePipelineStore();
  const [statusMessage, setStatusMessage] = useState('Preparing pipeline…');

  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;
    let finished = false;

    const start = async () => {
      let closeSocket = () => {};
      setStatusMessage('Connecting to progress events…');

      try {
        const socket = await connectProgress(sessionId, (event: ProgressEvent) => {
          switch (event.event) {
            case 'stage_started':
              setStageStarted(event.stage as string);
              setStatusMessage(`Running ${STAGE_LABELS[event.stage as string] ?? event.stage}…`);
              break;
            case 'stage_completed':
              setStageCompleted(event.stage as string, (event.metrics as Record<string, number>) ?? {});
              setStatusMessage(`Completed ${STAGE_LABELS[event.stage as string] ?? event.stage}`);
              break;
            case 'page_layout_detected':
              setPageLayout(
                event.page_id as string,
                event.page_index as number,
                event.total_pages as number,
                (event.blocks as BlockOverlay[]) ?? [],
                event.page_width as number,
                event.page_height as number,
              );
              break;
            case 'run_completed':
              finished = true;
              finishRun();
              closeSocket();
              onComplete();
              break;
            case 'run_failed':
              finished = true;
              if (event.stage) setStageError(event.stage);
              setError((event.error as string) ?? 'Pipeline failed');
              closeSocket();
              break;
            case 'run_cancelled':
              finished = true;
              finishRun();
              closeSocket();
              break;
          }
        });

        wsRef.current = socket.ws;
        closeSocket = socket.close;

        socket.ws.onerror = () => {
          if (!finished) setError('WebSocket connection lost');
        };

        socket.ws.onclose = () => {
          if (!finished && !error && !cancelled) {
            setError('Progress connection closed unexpectedly');
          }
        };

        const resp = await api.startProcessing(sessionId);
        if (cancelled) return;
        startRun(resp.run_id, sessionId);
        setStatusMessage('Pipeline started…');
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to start pipeline');
        }
      } finally {
        if (!finished) {
          closeSocket();
        }
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
    try { await api.cancelRun(sessionId, runId); } catch { /* ignore */ }
  };

  const layoutStage = stages.find((s) => s.stage === 'detect_layout');
  const layoutDone = layoutStage?.status === 'completed';

  return (
    <main style={{ display: 'flex', gap: '1.5rem', padding: '2rem', minHeight: '100vh', boxSizing: 'border-box' }}>
      {/* ── Left: canvas + legend ─────────────────────────────────────────── */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <h1 style={{ marginTop: 0, marginBottom: '0.75rem', fontSize: '1.4rem' }}>Processing</h1>

        {currentPageId ? (
          <>
            <p style={{ fontSize: '0.82rem', color: '#666', margin: '0 0 0.5rem' }}>
              Page {currentPageIndex + 1} of {totalPages || '?'}
              {!layoutDone && ' — detecting layout…'}
              {layoutDone && currentPageBlocks.length > 0 && ` — ${currentPageBlocks.length} block(s) detected`}
            </p>
            <LayoutCanvas
              sessionId={sessionId}
              pageId={currentPageId}
              blocks={currentPageBlocks}
              pageWidth={currentPageWidth}
              pageHeight={currentPageHeight}
              showBlocks={layoutDone}
            />
            {layoutDone && currentPageBlocks.length > 0 && (
              <BlockLegend blocks={currentPageBlocks} />
            )}
          </>
        ) : (
          <div style={placeholderStyle}>
            <span style={{ color: '#aaa', fontSize: '0.9rem' }}>
              Image preview will appear here after layout detection…
            </span>
          </div>
        )}
      </div>

      {/* ── Right: progress panel ─────────────────────────────────────────── */}
      <aside style={{ width: 270, flexShrink: 0 }}>
        <div style={{ marginBottom: '1rem' }}>
          <div style={{ marginBottom: '1rem', padding: '0.9rem 0.95rem', borderRadius: 10, background: '#f4f6fb', border: '1px solid #e2e8f0' }}>
          <strong style={{ display: 'block', marginBottom: '0.35rem', color: '#111' }}>
            {error ? 'Error' : isCancelling ? 'Cancelling pipeline' : isRunning ? 'Pipeline in progress' : 'Waiting for pipeline'}
          </strong>
          <p style={{ margin: 0, fontSize: '0.9rem', color: error ? '#cc0000' : '#4d5b6f' }}>
            {error ? error : statusMessage}
          </p>
        </div>
        <div style={{ background: '#e8e8e8', borderRadius: 8, height: 10, overflow: 'hidden' }}>
            <div
              style={{
                background: error ? '#cc0000' : '#0066cc',
                height: '100%',
                width: `${progressPercent}%`,
                transition: 'width 0.4s ease',
              }}
            />
          </div>
          <p style={{ fontSize: '0.8rem', color: '#666', margin: '0.3rem 0 0' }}>{progressPercent}%</p>
        </div>

        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {stages.map((st) => (
            <li key={st.stage} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.6rem', marginBottom: '0.55rem' }}>
              <StageIcon status={st.status} />
              <div>
                <span style={{ fontSize: '0.85rem', color: st.status === 'idle' ? '#aaa' : '#222' }}>
                  {STAGE_LABELS[st.stage] ?? st.stage}
                </span>
                {st.status === 'completed' && Object.keys(st.metrics).length > 0 && (
                  <MetricsBadge metrics={st.metrics} />
                )}
              </div>
            </li>
          ))}
        </ul>

        {error && <p style={{ color: '#cc0000', marginTop: '1rem', fontSize: '0.85rem' }}>{error}</p>}

        {isRunning && !isCancelling && (
          <button onClick={handleCancel} style={cancelBtnStyle}>Cancel</button>
        )}
        {isCancelling && <p style={{ color: '#888', fontSize: '0.8rem', marginTop: '0.75rem' }}>Cancelling…</p>}
      </aside>
    </main>
  );
}

// ─── Canvas component ─────────────────────────────────────────────────────────

interface CanvasProps {
  sessionId: string;
  pageId: string;
  blocks: BlockOverlay[];
  pageWidth: number;
  pageHeight: number;
  showBlocks: boolean;
}

function LayoutCanvas({ sessionId, pageId, blocks, pageWidth, pageHeight, showBlocks }: CanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  // Resolve the image URL when pageId changes
  useEffect(() => {
    let active = true;
    getPageImageUrl(sessionId, pageId).then((url) => {
      if (active) setImageUrl(url);
    });
    return () => { active = false; };
  }, [sessionId, pageId]);

  // Redraw when image URL or blocks change
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !imageUrl) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      const canvasW = canvas.width;
      const canvasH = canvas.height;

      // Scale image to fit canvas while preserving aspect ratio
      const srcW = pageWidth || img.naturalWidth;
      const srcH = pageHeight || img.naturalHeight;
      const scale = Math.min(canvasW / srcW, canvasH / srcH);
      const drawW = srcW * scale;
      const drawH = srcH * scale;
      const offsetX = (canvasW - drawW) / 2;
      const offsetY = (canvasH - drawH) / 2;

      ctx.clearRect(0, 0, canvasW, canvasH);
      ctx.fillStyle = '#f5f5f5';
      ctx.fillRect(0, 0, canvasW, canvasH);
      ctx.drawImage(img, offsetX, offsetY, drawW, drawH);

      if (!showBlocks || blocks.length === 0) return;

      for (const block of blocks) {
        const color = BLOCK_COLORS[block.block_type] ?? FALLBACK_COLOR;
        const bx = offsetX + block.bbox.x * scale;
        const by = offsetY + block.bbox.y * scale;
        const bw = block.bbox.width * scale;
        const bh = block.bbox.height * scale;

        ctx.fillStyle = color.fill;
        ctx.fillRect(bx, by, bw, bh);

        ctx.strokeStyle = color.stroke;
        ctx.lineWidth = 1.5;
        ctx.strokeRect(bx, by, bw, bh);

        // Type label in top-left corner of the block
        const label = color.label;
        ctx.font = 'bold 10px system-ui, sans-serif';
        const textW = ctx.measureText(label).width;
        ctx.fillStyle = color.stroke;
        ctx.fillRect(bx, by, textW + 6, 15);
        ctx.fillStyle = '#fff';
        ctx.fillText(label, bx + 3, by + 11);
      }
    };
    img.onerror = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#fee';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#c00';
      ctx.font = '13px system-ui';
      ctx.fillText('Failed to load image', 12, 24);
    };
    img.src = imageUrl;
  }, [imageUrl, blocks, showBlocks, pageWidth, pageHeight]);

  return (
    <canvas
      ref={canvasRef}
      width={680}
      height={500}
      style={{ display: 'block', border: '1px solid #ddd', borderRadius: 6, maxWidth: '100%', background: '#f5f5f5' }}
    />
  );
}

// ─── Block legend ─────────────────────────────────────────────────────────────

function BlockLegend({ blocks }: { blocks: BlockOverlay[] }) {
  const types = [...new Set(blocks.map((b) => b.block_type))];
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.6rem' }}>
      {types.map((t) => {
        const color = BLOCK_COLORS[t] ?? FALLBACK_COLOR;
        return (
          <span
            key={t}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '0.3rem',
              padding: '2px 7px', borderRadius: 10,
              background: color.fill, border: `1px solid ${color.stroke}`,
              fontSize: '0.75rem', color: '#333',
            }}
          >
            <span style={{ width: 8, height: 8, borderRadius: 2, background: color.stroke, display: 'inline-block' }} />
            {color.label} ({blocks.filter((b) => b.block_type === t).length})
          </span>
        );
      })}
    </div>
  );
}

// ─── Stage icon ───────────────────────────────────────────────────────────────

function StageIcon({ status }: { status: string }) {
  const icons: Record<string, string> = {
    idle: '○', running: '◌', completed: '●', failed: '✕', cancelled: '—',
  };
  const colors: Record<string, string> = {
    idle: '#ccc', running: '#0066cc', completed: '#007744', failed: '#cc0000', cancelled: '#888',
  };
  return (
    <span style={{ color: colors[status] ?? '#ccc', fontSize: '1rem', width: 18, textAlign: 'center', flexShrink: 0, marginTop: 1 }}>
      {icons[status] ?? '○'}
    </span>
  );
}

// ─── Metrics badge ────────────────────────────────────────────────────────────

function MetricsBadge({ metrics }: { metrics: Record<string, number> }) {
  const entries = Object.entries(metrics)
    .filter(([k]) => k !== 'elapsed_s')
    .slice(0, 3);
  const elapsed = metrics['elapsed_s'];
  return (
    <div style={{ fontSize: '0.72rem', color: '#888', marginTop: 1 }}>
      {entries.map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`).join(' · ')}
      {elapsed !== undefined && ` · ${elapsed.toFixed(1)}s`}
    </div>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const placeholderStyle: React.CSSProperties = {
  width: 680, height: 500, maxWidth: '100%',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  border: '1px dashed #ccc', borderRadius: 6, background: '#fafafa',
};

const cancelBtnStyle: React.CSSProperties = {
  marginTop: '1.5rem', padding: '0.5rem 1.2rem',
  background: '#fff', border: '1px solid #ccc', borderRadius: 6,
  cursor: 'pointer', fontSize: '0.875rem',
};
