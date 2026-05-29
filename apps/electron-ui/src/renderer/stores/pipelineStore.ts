import { create } from 'zustand';

export type StageStatus = 'idle' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface StageState {
  stage: string;
  status: StageStatus;
  metrics: Record<string, number>;
}

export interface BlockOverlay {
  block_type: string;
  bbox: { x: number; y: number; width: number; height: number };
  confidence: number;
}

export interface RunMetrics {
  totalElapsedS: number;
  stageCount: number;
  slowestStage: string | null;
  slowestStageS: number;
}

interface PipelineState {
  runId: string | null;
  sessionId: string | null;
  stages: StageState[];
  progressPercent: number;
  isRunning: boolean;
  isCancelling: boolean;
  error: string | null;

  // Canvas overlay state — populated from page_layout_detected WS events
  currentPageId: string | null;
  currentPageIndex: number;
  totalPages: number;
  currentPageWidth: number;
  currentPageHeight: number;
  currentPageBlocks: BlockOverlay[];

  runMetrics: RunMetrics | null;

  startRun: (runId: string, sessionId: string) => void;
  setStageStarted: (stage: string) => void;
  setStageCompleted: (stage: string, metrics: Record<string, number>) => void;
  setStageError: (stage: string) => void;
  setError: (error: string) => void;
  setRunMetrics: (metrics: RunMetrics) => void;
  requestCancel: () => void;
  finishRun: () => void;
  reset: () => void;
  setPageLayout: (
    pageId: string,
    pageIndex: number,
    totalPages: number,
    blocks: BlockOverlay[],
    pageWidth: number,
    pageHeight: number,
  ) => void;
}

export const PIPELINE_STAGES = [
  'import',
  'preprocess',
  'detect_layout',
  'recognize_text',
  'text_correction',
  'reconstruct_structure',
  'detect_diagrams',
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

  currentPageId: null,
  currentPageIndex: 0,
  totalPages: 0,
  currentPageWidth: 0,
  currentPageHeight: 0,
  currentPageBlocks: [],

  runMetrics: null,

  startRun: (runId, sessionId) =>
    set({
      runId,
      sessionId,
      stages: initialStages(),
      progressPercent: 0,
      isRunning: true,
      isCancelling: false,
      error: null,
      currentPageId: null,
      currentPageBlocks: [],
      runMetrics: null,
    }),

  setStageStarted: (stage) =>
    set((s) => ({
      stages: s.stages.map((st) => (st.stage === stage ? { ...st, status: 'running' } : st)),
    })),

  setStageCompleted: (stage, metrics) =>
    set((s) => {
      const updated = s.stages.map((st) =>
        st.stage === stage ? { ...st, status: 'completed' as StageStatus, metrics } : st,
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
  setRunMetrics: (runMetrics) => set({ runMetrics }),
  requestCancel: () => set({ isCancelling: true }),
  finishRun: () => set({ isRunning: false, progressPercent: 100, isCancelling: false }),
  reset: () =>
    set({
      runId: null,
      sessionId: null,
      stages: initialStages(),
      progressPercent: 0,
      isRunning: false,
      isCancelling: false,
      error: null,
      currentPageId: null,
      currentPageBlocks: [],
      runMetrics: null,
    }),

  setPageLayout: (pageId, pageIndex, totalPages, blocks, pageWidth, pageHeight) =>
    set({ currentPageId: pageId, currentPageIndex: pageIndex, totalPages, currentPageBlocks: blocks, currentPageWidth: pageWidth, currentPageHeight: pageHeight }),
}));
