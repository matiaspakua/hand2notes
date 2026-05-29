import { useEffect, useRef, useState } from 'react';
import { api, connectProgress, getPageImageUrl } from '../services/api';
import type { ProgressEvent } from '../services/types';
import { usePipelineStore, type BlockOverlay } from '../stores/pipelineStore';
import { stageMeta } from '../lib/pipelineViz';
import { ProgressRing } from '../components/ProgressRing';
import { PipelineTimeline } from '../components/PipelineTimeline';
import { StageTimingChart } from '../components/StageTimingChart';
import { ConversionStats } from '../components/ConversionStats';
import '../styles/pipeline.css';

// ─── Block type colours (translucent fills + solid border) ───────────────────
const BLOCK_COLORS: Record<string, { fill: string; stroke: string; label: string }> = {
  title:          { fill: 'rgba(99,102,241,0.30)',  stroke: 'rgba(129,140,248,0.95)', label: 'Title' },
  heading:        { fill: 'rgba(14,165,233,0.28)',  stroke: 'rgba(56,189,248,0.95)',  label: 'Heading' },
  paragraph:      { fill: 'rgba(34,197,94,0.20)',   stroke: 'rgba(74,222,128,0.9)',   label: 'Paragraph' },
  bullet_list:    { fill: 'rgba(16,185,129,0.26)',  stroke: 'rgba(52,211,153,0.95)',  label: 'List' },
  numbered_list:  { fill: 'rgba(13,148,136,0.26)',  stroke: 'rgba(45,212,191,0.95)',  label: 'Numbered List' },
  table:          { fill: 'rgba(245,158,11,0.32)',  stroke: 'rgba(251,191,36,0.95)',  label: 'Table' },
  diagram:        { fill: 'rgba(239,68,68,0.32)',   stroke: 'rgba(248,113,113,0.95)', label: 'Diagram' },
  formula:        { fill: 'rgba(217,119,6,0.32)',   stroke: 'rgba(251,146,60,0.95)',  label: 'Formula' },
  callout:        { fill: 'rgba(236,72,153,0.26)',  stroke: 'rgba(244,114,182,0.95)', label: 'Callout' },
  marginal_note:  { fill: 'rgba(148,163,184,0.26)', stroke: 'rgba(203,213,225,0.9)',  label: 'Note' },
  url_reference:  { fill: 'rgba(6,182,212,0.30)',   stroke: 'rgba(34,211,238,0.95)',  label: 'URL' },
  embedded_image: { fill: 'rgba(249,115,22,0.26)',  stroke: 'rgba(251,146,60,0.95)',  label: 'Image' },
  arrow_connector:{ fill: 'rgba(100,116,139,0.24)', stroke: 'rgba(148,163,184,0.9)',  label: 'Arrow' },
};
const FALLBACK_COLOR = { fill: 'rgba(120,120,120,0.25)', stroke: 'rgba(148,163,184,0.85)', label: 'Block' };

interface Props {
  sessionId: string;
  onComplete: () => void;
}

export function ProcessingPage({ sessionId, onComplete }: Props) {
  const {
    runId, stages, progressPercent, isRunning, isCancelling, error,
    currentPageId, currentPageIndex, totalPages,
    currentPageWidth, currentPageHeight, currentPageBlocks, runMetrics,
    startRun, setStageStarted, setStageCompleted, setStageError, setError,
    setRunMetrics, requestCancel, finishRun, setPageLayout,
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
              setStatusMessage(`Running ${stageMeta(event.stage as string).label}…`);
              break;
            case 'stage_completed':
              setStageCompleted(event.stage as string, (event.metrics as Record<string, number>) ?? {});
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
            case 'run_metrics':
              setRunMetrics({
                totalElapsedS: event.total_elapsed_s ?? 0,
                stageCount: event.stage_count ?? 0,
                slowestStage: event.slowest_stage ?? null,
                slowestStageS: event.slowest_stage_s ?? 0,
              });
              break;
            case 'run_completed':
              finished = true;
              finishRun();
              setStatusMessage('Conversion complete');
              closeSocket();
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
        socket.ws.onerror = () => { if (!finished) setError('WebSocket connection lost'); };
        socket.ws.onclose = () => {
          if (!finished && !error && !cancelled) setError('Progress connection closed unexpectedly');
        };

        const resp = await api.startProcessing(sessionId);
        if (cancelled) return;
        startRun(resp.run_id, sessionId);
        setStatusMessage('Pipeline started…');
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to start pipeline');
      } finally {
        if (!finished) closeSocket();
      }
    };

    void start();
    return () => { cancelled = true; wsRef.current?.close(); };
  }, [sessionId]);

  const handleCancel = async () => {
    if (!runId) return;
    requestCancel();
    try { await api.cancelRun(sessionId, runId); } catch { /* ignore */ }
  };

  const layoutDone = stages.find((s) => s.stage === 'detect_layout')?.status === 'completed';
  const isDone = !isRunning && progressPercent === 100 && !error;
  const statusText = error ? 'Error'
    : isCancelling ? 'Cancelling…'
    : isDone ? 'Done'
    : isRunning ? 'Converting' : 'Starting';

  return (
    <main className="h2n-processing">
      {/* ── Left: live page canvas ──────────────────────────────────────── */}
      <section style={{ minWidth: 0 }}>
        <h1 className="h2n-title">Converting your notes</h1>
        <p className="h2n-subtitle">
          {currentPageId
            ? `Page ${currentPageIndex + 1} of ${totalPages || '?'}${
                layoutDone && currentPageBlocks.length ? ` — ${currentPageBlocks.length} regions detected` : ''}`
            : 'Watch each stage transform the handwritten page into structured Markdown.'}
        </p>

        <div className="h2n-card" style={{ padding: '1rem' }}>
          {currentPageId ? (
            <LayoutCanvas
              sessionId={sessionId}
              pageId={currentPageId}
              blocks={currentPageBlocks}
              pageWidth={currentPageWidth}
              pageHeight={currentPageHeight}
              showBlocks={!!layoutDone}
            />
          ) : (
            <div className="h2n-placeholder">
              <div style={{ textAlign: 'center' }}>
                <span className="h2n-spinner" />
                <p style={{ marginTop: '0.75rem' }}>Detecting the page layout…</p>
              </div>
            </div>
          )}
          {layoutDone && currentPageBlocks.length > 0 && <BlockLegend blocks={currentPageBlocks} />}
        </div>

        {(isDone || runMetrics) && (
          <div className="h2n-card">
            <p className="h2n-card-title">Stage timing</p>
            <StageTimingChart stages={stages} />
          </div>
        )}
      </section>

      {/* ── Right: progress panel ───────────────────────────────────────── */}
      <aside>
        <div className="h2n-card">
          <ProgressRing percent={progressPercent} status={statusText} subtitle={error ?? statusMessage} />
        </div>

        <div className="h2n-card">
          <p className="h2n-card-title">Pipeline</p>
          <PipelineTimeline stages={stages} />
        </div>

        {isDone && (
          <div className="h2n-card">
            <p className="h2n-card-title">Outcome</p>
            <ConversionStats stages={stages} runMetrics={runMetrics} blockCount={currentPageBlocks.length} />
            <button className="h2n-btn h2n-btn-primary" onClick={onComplete} style={{ marginTop: '1rem' }}>
              View exported notes →
            </button>
          </div>
        )}

        {error && <p className="h2n-error">{error}</p>}
        {isRunning && !isCancelling && (
          <button className="h2n-btn" onClick={handleCancel}>Cancel</button>
        )}
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

  useEffect(() => {
    let active = true;
    getPageImageUrl(sessionId, pageId).then((url) => { if (active) setImageUrl(url); });
    return () => { active = false; };
  }, [sessionId, pageId]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !imageUrl) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      const canvasW = canvas.width;
      const canvasH = canvas.height;
      const srcW = pageWidth || img.naturalWidth;
      const srcH = pageHeight || img.naturalHeight;
      const scale = Math.min(canvasW / srcW, canvasH / srcH);
      const drawW = srcW * scale;
      const drawH = srcH * scale;
      const offsetX = (canvasW - drawW) / 2;
      const offsetY = (canvasH - drawH) / 2;

      ctx.clearRect(0, 0, canvasW, canvasH);
      ctx.fillStyle = '#0f1626';
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
        const label = color.label;
        ctx.font = 'bold 10px system-ui, sans-serif';
        const textW = ctx.measureText(label).width;
        ctx.fillStyle = color.stroke;
        ctx.fillRect(bx, by, textW + 6, 15);
        ctx.fillStyle = '#0b1020';
        ctx.fillText(label, bx + 3, by + 11);
      }
    };
    img.onerror = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#1a1020';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = '#fca5a5';
      ctx.font = '13px system-ui';
      ctx.fillText('Failed to load image', 12, 24);
    };
    img.src = imageUrl;
  }, [imageUrl, blocks, showBlocks, pageWidth, pageHeight]);

  return <canvas ref={canvasRef} width={720} height={520} className="h2n-canvas" />;
}

function BlockLegend({ blocks }: { blocks: BlockOverlay[] }) {
  const types = [...new Set(blocks.map((b) => b.block_type))];
  return (
    <div className="h2n-legend">
      {types.map((t) => {
        const color = BLOCK_COLORS[t] ?? FALLBACK_COLOR;
        return (
          <span key={t} className="h2n-chip">
            <span className="h2n-chip-dot" style={{ background: color.stroke }} />
            {color.label} ({blocks.filter((b) => b.block_type === t).length})
          </span>
        );
      })}
    </div>
  );
}
