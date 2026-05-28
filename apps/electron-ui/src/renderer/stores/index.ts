// Root Zustand store composed of feature slices. Each slice is expanded by its
// owning user story (session → US1, pipeline → US1, review → US6).

import { create } from 'zustand';
import type { PipelineRun, ProgressEvent, ReviewPayload, Session } from '../services/types';

export interface SessionSlice {
  currentSession: Session | null;
  sessions: Session[];
  setCurrentSession: (session: Session | null) => void;
  setSessions: (sessions: Session[]) => void;
}

export interface PipelineSlice {
  currentRun: PipelineRun | null;
  progress: ProgressEvent | null;
  setCurrentRun: (run: PipelineRun | null) => void;
  setProgress: (event: ProgressEvent | null) => void;
}

export interface ReviewSlice {
  reviewPage: ReviewPayload | null;
  setReviewPage: (page: ReviewPayload | null) => void;
}

export type AppStore = SessionSlice & PipelineSlice & ReviewSlice;

export const useAppStore = create<AppStore>((set) => ({
  // session slice
  currentSession: null,
  sessions: [],
  setCurrentSession: (currentSession) => set({ currentSession }),
  setSessions: (sessions) => set({ sessions }),

  // pipeline slice
  currentRun: null,
  progress: null,
  setCurrentRun: (currentRun) => set({ currentRun }),
  setProgress: (progress) => set({ progress }),

  // review slice
  reviewPage: null,
  setReviewPage: (reviewPage) => set({ reviewPage }),
}));
