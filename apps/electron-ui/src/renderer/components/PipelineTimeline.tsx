import type { StageState } from '../stores/pipelineStore';
import { formatDuration, headlineMetrics, stageMeta } from '../lib/pipelineViz';

const STATUS_CLASS: Record<string, string> = {
  idle: 'idle', running: 'running', completed: 'done', failed: 'failed', cancelled: 'idle',
};

const DOT: Record<string, string> = {
  idle: '', running: '', completed: '✓', failed: '✕', cancelled: '—',
};

/** Vertical animated stage tracker with per-stage metrics and timing. */
export function PipelineTimeline({ stages }: { stages: StageState[] }) {
  return (
    <ul className="h2n-timeline">
      {stages.map((st) => {
        const meta = stageMeta(st.stage);
        const cls = STATUS_CLASS[st.status] ?? 'idle';
        const elapsed = st.metrics.elapsed_s;
        const metrics = headlineMetrics(st.metrics);
        return (
          <li key={st.stage} className={`h2n-stage ${cls}`}>
            <span className="h2n-dot" aria-hidden>
              {st.status === 'running' ? <span className="h2n-spinner" style={{ width: 12, height: 12 }} />
                : st.status === 'completed' ? DOT.completed
                : st.status === 'failed' ? DOT.failed
                : meta.icon}
            </span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <span className="h2n-stage-label">{meta.label}</span>
              {st.status === 'completed' && metrics.length > 0 && (
                <div className="h2n-stage-metrics">
                  {metrics.map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`).join(' · ')}
                </div>
              )}
            </div>
            {st.status === 'completed' && elapsed !== undefined && (
              <span className="h2n-stage-time">{formatDuration(elapsed)}</span>
            )}
          </li>
        );
      })}
    </ul>
  );
}
