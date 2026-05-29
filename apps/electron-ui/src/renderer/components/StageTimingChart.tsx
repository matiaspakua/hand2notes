import type { StageState } from '../stores/pipelineStore';
import { buildTimingChart, formatDuration } from '../lib/pipelineViz';

/** Animated horizontal bar chart of per-stage elapsed time. */
export function StageTimingChart({ stages }: { stages: StageState[] }) {
  const bars = buildTimingChart(stages);
  if (bars.length === 0) {
    return <p style={{ color: 'var(--text-dim)', fontSize: '0.8rem', margin: 0 }}>Timing data appears as stages complete…</p>;
  }
  return (
    <div>
      {bars.map((bar, i) => (
        <div className="h2n-bar-row" key={bar.stage}>
          <span className="h2n-bar-label" title={bar.stage}>{bar.label}</span>
          <div className="h2n-bar-track">
            <div
              className="h2n-bar-fill"
              style={{
                width: `${Math.max(4, bar.fraction * 100)}%`,
                background: bar.accent,
                animationDelay: `${i * 70}ms`,
              }}
              title={`${bar.share}% of total`}
            />
          </div>
          <span className="h2n-bar-val">{formatDuration(bar.seconds)}</span>
        </div>
      ))}
    </div>
  );
}
