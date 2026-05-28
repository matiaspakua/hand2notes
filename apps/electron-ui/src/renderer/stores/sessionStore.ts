import { create } from 'zustand';
import type { Session, Page } from '../services/types';

interface SessionState {
  sessions: Session[];
  currentSession: Session | null;
  currentPages: Page[];
  isLoading: boolean;
  error: string | null;

  setCurrentSession: (session: Session | null) => void;
  setCurrentPages: (pages: Page[]) => void;
  setSessions: (sessions: Session[]) => void;
  addSession: (session: Session) => void;
  updateSession: (session: Session) => void;
  removeSession: (sessionId: string) => void;
  addPages: (pages: Page[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  currentSession: null,
  currentPages: [],
  isLoading: false,
  error: null,

  setCurrentSession: (session) => set({ currentSession: session }),
  setCurrentPages: (pages) => set({ currentPages: pages }),
  setSessions: (sessions) => set({ sessions }),
  addSession: (session) => set((s) => ({ sessions: [...s.sessions, session] })),
  updateSession: (updated) =>
    set((s) => ({
      sessions: s.sessions.map((sess) => (sess.id === updated.id ? updated : sess)),
      currentSession: s.currentSession?.id === updated.id ? updated : s.currentSession,
    })),
  removeSession: (sessionId) =>
    set((s) => ({
      sessions: s.sessions.filter((sess) => sess.id !== sessionId),
      currentSession: s.currentSession?.id === sessionId ? null : s.currentSession,
    })),
  addPages: (pages) => set((s) => ({ currentPages: [...s.currentPages, ...pages] })),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  reset: () => set({ currentSession: null, currentPages: [], error: null }),
}));
