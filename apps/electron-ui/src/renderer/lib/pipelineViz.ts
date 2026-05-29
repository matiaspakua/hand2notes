// Pure helpers for the processing visualisation — no React/DOM, fully unit-testable.

import type { StageState } from '../stores/pipelineStore';

export interface StageMeta {
  label: string;
  short: string;
  icon: string;
  accent: string; // CSS colour used for the stage accent / chart bar
}

/** Display metadata for each pipeline stage, in execution order. */
export const STAGE_META: Record<string, StageMeta> = {
  import: { label: 'Importing images', short: 'Import', icon: '📥', accent: '#6366f1' },
  preprocess: { label: 'Preprocessing (deskew & resize)', short: 'Preprocess', icon: '🪄', accent: '#8b5cf6' },
  detect_layout: { label: 'Detecting layout regions', short: 'Layout', icon: '🧭', accent: '#0ea5e9' },
  recognize_text: { label: 'Recognizing text (VLM OCR)', short: 'OCR', icon: '✍️', accent: '#06b6d4' },
  text_correction: { label: 'Correcting text (ES/EN)', short: 'Correct', icon: '🔤', accent: '#10b981' },
  reconstruct_structure: { label: 'Reconstructing structure', short: 'Structure', icon: '🧩', accent: '#22c55e' },
  detect_diagrams: { label: 'Interpreting diagrams', short: 'Diagrams', icon: '🔀', accent: '#f59e0b' },
  generate_output: { label: 'Generating Markdown', short: 'Output', icon: '📝', accent: '#ef4444' },
};

export function stageMeta(stage: string): StageMeta {
  return STAGE_META[stage] ?? { label: stage, short: stage, icon: '•', accent: '#94a3b8' };
}

/** Format a duration in seconds for display ("0.4s", "1.2s", "1m 05s"). */
export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '—';
  if (seconds < 60) return `${seconds.toFixed(seconds < 10 ? 1 : 0)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${String(s).padStart(2, '0')}s`;
}

export interface ChartBar {
  stage: string;
  label: string;
  accent: string;
  seconds: number;
  /** Width as a fraction (0–1) of the slowest bar — for the chart layout. */
  fraction: number;
  /** Percentage of total runtime this stage represents (0–100, rounded). */
  share: number;
}

/**
 * Build horizontal-bar-chart data from completed stage timings. Bars are scaled
 * to the slowest stage so the longest stage fills the track; `share` is the
 * portion of total runtime. Stages without a timing yet are omitted.
 */
export function buildTimingChart(stages: StageState[]): ChartBar[] {
  const timed = stages
    .map((st) => ({ stage: st.stage, seconds: st.metrics.elapsed_s ?? 0 }))
    .filter((b) => b.seconds > 0);
  if (timed.length === 0) return [];
  const max = Math.max(...timed.map((b) => b.seconds));
  const total = timed.reduce((sum, b) => sum + b.seconds, 0);
  return timed.map((b) => {
    const meta = stageMeta(b.stage);
    return {
      stage: b.stage,
      label: meta.short,
      accent: meta.accent,
      seconds: b.seconds,
      fraction: max > 0 ? b.seconds / max : 0,
      share: total > 0 ? Math.round((b.seconds / total) * 100) : 0,
    };
  });
}

/** Total elapsed time across all completed stages. */
export function totalElapsed(stages: StageState[]): number {
  return stages.reduce((sum, st) => sum + (st.metrics.elapsed_s ?? 0), 0);
}

/** Pick out a few headline metrics from a stage's metrics map for display. */
export function headlineMetrics(metrics: Record<string, number>, limit = 3): [string, number][] {
  return Object.entries(metrics)
    .filter(([k]) => k !== 'elapsed_s')
    .slice(0, limit);
}
