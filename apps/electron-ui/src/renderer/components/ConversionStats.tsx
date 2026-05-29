import type { RunMetrics, StageState } from '../stores/pipelineStore';
import { formatDuration, stageMeta, totalElapsed } from '../lib/pipelineViz';

interface Props {
  stages: StageState[];
  runMetrics: RunMetrics | null;
  blockCount: number;
}

function metricValue(stages: StageState[], stage: string, key: string): number {
  return stages.find((s) => s.stage === stage)?.metrics[key] ?? 0;
}

/** Headline outcome tiles shown as the conversion completes. */
export function ConversionStats({ stages, runMetrics, blockCount }: Props) {
  const total = runMetrics?.totalElapsedS ?? totalElapsed(stages);
  const diagrams = metricValue(stages, 'detect_diagrams', 'diagrams_found');
  const tiles: { value: string; label: string }[] = [
    { value: formatDuration(total), label: 'Total time' },
    { value: String(blockCount || metricValue(stages, 'recognize_text', 'blocks_recognized')), label: 'Blocks' },
    { value: String(diagrams), label: 'Diagrams' },
  ];
  return (
    <div>
      <div className="h2n-stats">
        {tiles.map((t, i) => (
          <div className="h2n-stat" key={t.label} style={{ animationDelay: `${i * 80}ms` }}>
            <div className="h2n-stat-value">{t.value}</div>
            <div className="h2n-stat-label">{t.label}</div>
          </div>
        ))}
      </div>
      {runMetrics?.slowestStage && (
        <p style={{ color: 'var(--text-dim)', fontSize: '0.76rem', margin: '0.75rem 0 0' }}>
          Slowest stage: <strong style={{ color: 'var(--text)' }}>{stageMeta(runMetrics.slowestStage).short}</strong>
          {' '}({formatDuration(runMetrics.slowestStageS)})
        </p>
      )}
    </div>
  );
}
