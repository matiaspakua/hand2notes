import { create } from 'zustand';

interface BlockData {
  block_id: string;
  block_type: string;
  content: string | null;
  corrected_content: string | null;
  confidence: number;
  review_flag: boolean;
  reading_order: number;
}

import type { DiagramDecision } from '../components/DiagramPreview';

interface DiagramPreviewData {
  block_id: string;
  diagram_type: string;
  crop_path: string | null;
  generated_source_path: string | null;
  reconstruction_confidence: number;
  review_decision: DiagramDecision;
}

interface PageReviewData {
  session_id: string;
  page_id: string;
  sequence: number;
  source_url: string;
  preprocessed_url: string | null;
  overall_confidence: number;
  review_status: string;
  markdown_preview: string;
  blocks: BlockData[];
  diagram_previews: DiagramPreviewData[];
}

interface ReviewState {
  currentPageData: PageReviewData | null;
  correctionDrafts: Record<string, string>;
  diagramDecisions: Record<string, string>;
  loading: boolean;
  error: string | null;

  loadPageReview: (apiBase: string, sessionId: string, pageId: string) => Promise<void>;
  setDraft: (blockId: string, content: string) => void;
  setDiagramDecision: (blockId: string, decision: string) => void;
  isReviewComplete: () => boolean;
  reset: () => void;
}

export const useReviewStore = create<ReviewState>((set, get) => ({
  currentPageData: null,
  correctionDrafts: {},
  diagramDecisions: {},
  loading: false,
  error: null,

  loadPageReview: async (apiBase, sessionId, pageId) => {
    set({ loading: true, error: null });
    try {
      const res = await fetch(`${apiBase}/sessions/${sessionId}/pages/${pageId}/review`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: PageReviewData = await res.json();
      // Seed diagram decisions from loaded data
      const decisions: Record<string, string> = {};
      for (const dp of data.diagram_previews) {
        decisions[dp.block_id] = dp.review_decision;
      }
      set({ currentPageData: data, diagramDecisions: decisions, loading: false });
    } catch (e) {
      set({ error: String(e), loading: false });
    }
  },

  setDraft: (blockId, content) =>
    set(state => ({ correctionDrafts: { ...state.correctionDrafts, [blockId]: content } })),

  setDiagramDecision: (blockId, decision) =>
    set(state => ({ diagramDecisions: { ...state.diagramDecisions, [blockId]: decision } })),

  isReviewComplete: () => {
    const { currentPageData, diagramDecisions } = get();
    if (!currentPageData) return false;
    // Check no text blocks are still flagged
    const anyFlagged = currentPageData.blocks.some(b => b.review_flag);
    if (anyFlagged) return false;
    // Check all diagrams have a decision (not pending)
    const anyPending = currentPageData.diagram_previews.some(
      dp => (diagramDecisions[dp.block_id] ?? dp.review_decision) === 'pending'
    );
    return !anyPending;
  },

  reset: () => set({
    currentPageData: null,
    correctionDrafts: {},
    diagramDecisions: {},
    loading: false,
    error: null,
  }),
}));
