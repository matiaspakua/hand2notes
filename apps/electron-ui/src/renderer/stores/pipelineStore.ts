import { create } from 'zustand';

export type StageStatus = 'idle' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface StageState {
  stage: string;
  status: StageStatus;
  metrics: Record<string, number>;
}

interface PipelineState {
  runId: string | null;
  sessionId: string | null;
  stages: StageState[];
  progressPercent: number;
  isRunning: boolean;
  isCancelling: boolean;
  error: string | null;

  startRun: (runId: string, sessionId: string) => void;
  setStageStarted: (stage: string) => void;
  setStageCompleted: (stage: string, metrics: Record<string, number>) => void;
  setStageError: (stage: string) => void;
  setError: (error: string) => void;
  requestCancel: () => void;
  finishRun: () => void;
  reset: () => void;
}

const PIPELINE_STAGES = [
  'import',
  'preprocess',
  'detect_layout',
  'recognize_text',
  'reconstruct_structure',
  'generate_output',
];

const initialStages = (): StageState[] =>
  PIPELINE_STAGES.map((stage) => ({ stage, status: 'idle', metrics: {} }));

export const usePipelineStore = create<PipelineState>((set) => ({
  runId: null,
  sessionId: null,
  stages: initialStages(),
  progressPercent: 0,
  isRunning: false,
  isCancelling: false,
  error: null,

  startRun: (runId, sessionId) =>
    set({ runId, sessionId, stages: initialStages(), progressPercent: 0, isRunning: true, isCancelling: false, error: null }),

  setStageStarted: (stage) =>
    set((s) => ({
      stages: s.stages.map((st) => (st.stage === stage ? { ...st, status: 'running' } : st)),
    })),

  setStageCompleted: (stage, metrics) =>
    set((s) => {
      const updated = s.stages.map((st) =>
        st.stage === stage ? { ...st, status: 'completed' as StageStatus, metrics } : st
      );
      const completed = updated.filter((st) => st.status === 'completed').length;
      return { stages: updated, progressPercent: Math.round((completed / PIPELINE_STAGES.length) * 100) };
    }),

  setStageError: (stage) =>
    set((s) => ({
      stages: s.stages.map((st) => (st.stage === stage ? { ...st, status: 'failed' } : st)),
      isRunning: false,
    })),

  setError: (error) => set({ error, isRunning: false }),
  requestCancel: () => set({ isCancelling: true }),
  finishRun: () => set({ isRunning: false, progressPercent: 100, isCancelling: false }),
  reset: () => set({ runId: null, sessionId: null, stages: initialStages(), progressPercent: 0, isRunning: false, isCancelling: false, error: null }),
}));
