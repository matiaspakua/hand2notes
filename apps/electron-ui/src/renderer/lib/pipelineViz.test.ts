import { describe, expect, it } from 'vitest';
import type { StageState } from '../stores/pipelineStore';
import {
  buildTimingChart,
  formatDuration,
  headlineMetrics,
  stageMeta,
  totalElapsed,
} from './pipelineViz';

function stage(name: string, elapsed?: number, extra: Record<string, number> = {}): StageState {
  return {
    stage: name,
    status: 'completed',
    metrics: elapsed === undefined ? extra : { elapsed_s: elapsed, ...extra },
  };
}

describe('formatDuration', () => {
  it('formats sub-minute durations', () => {
    expect(formatDuration(0.4)).toBe('0.4s');
    expect(formatDuration(12)).toBe('12s');
  });
  it('formats minute durations', () => {
    expect(formatDuration(65)).toBe('1m 05s');
  });
  it('handles invalid input', () => {
    expect(formatDuration(-1)).toBe('—');
    expect(formatDuration(NaN)).toBe('—');
  });
});

describe('stageMeta', () => {
  it('returns metadata for known stages', () => {
    expect(stageMeta('recognize_text').short).toBe('OCR');
  });
  it('falls back for unknown stages', () => {
    expect(stageMeta('mystery').label).toBe('mystery');
  });
});

describe('buildTimingChart', () => {
  it('returns empty when no stage has timing', () => {
    expect(buildTimingChart([stage('import')])).toEqual([]);
  });

  it('scales bars to the slowest stage and computes share', () => {
    const bars = buildTimingChart([
      stage('import', 1),
      stage('recognize_text', 3),
      stage('generate_output', 0),
    ]);
    expect(bars).toHaveLength(2); // zero-time stage excluded
    const ocr = bars.find((b) => b.stage === 'recognize_text')!;
    expect(ocr.fraction).toBe(1); // slowest → full width
    expect(ocr.share).toBe(75); // 3 of 4 total seconds
    const imp = bars.find((b) => b.stage === 'import')!;
    expect(imp.fraction).toBeCloseTo(1 / 3);
  });
});

describe('totalElapsed', () => {
  it('sums elapsed_s across stages', () => {
    expect(totalElapsed([stage('a', 1.5), stage('b', 2.5), stage('c')])).toBe(4);
  });
});

describe('headlineMetrics', () => {
  it('omits elapsed_s and limits count', () => {
    const m = headlineMetrics({ elapsed_s: 1, blocks: 5, urls: 2, extra: 9 }, 2);
    expect(m).toEqual([['blocks', 5], ['urls', 2]]);
  });
});
