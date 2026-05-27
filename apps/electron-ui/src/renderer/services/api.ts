// Typed HTTP + WebSocket client for the local hand2notes Python backend.
// The base URL is resolved lazily from the port the Electron main process
// learned when it spawned the backend (see preload `window.h2n.getApiPort`).

import type {
  AppConfig,
  CreateSessionRequest,
  PipelineRun,
  PipelineStage,
  ProgressEvent,
  ReviewPayload,
  Session,
  VaultValidation,
} from './types';

const API_PREFIX = '/api/v1';

class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

let cachedPort: number | null = null;

async function resolvePort(): Promise<number> {
  if (cachedPort != null) return cachedPort;
  const port = await window.h2n.getApiPort();
  if (port == null) throw new ApiError(0, 'backend_unavailable', 'Backend not ready');
  cachedPort = port;
  return port;
}

async function baseHttp(): Promise<string> {
  return `http://127.0.0.1:${await resolvePort()}${API_PREFIX}`;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const url = `${await baseHttp()}${path}`;
  const init: RequestInit = { method, headers: {} };
  if (body instanceof FormData) {
    init.body = body;
  } else if (body !== undefined) {
    (init.headers as Record<string, string>)['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  const res = await fetch(url, init);
  if (!res.ok) {
    const payload = await res.json().catch(() => null);
    const err = payload?.error;
    throw new ApiError(res.status, err?.code ?? 'http_error', err?.message ?? res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  // --- Sessions ---
  createSession: (req: CreateSessionRequest) => request<Session>('POST', '/sessions', req),
  listSessions: () => request<{ sessions: Session[]; total: number }>('GET', '/sessions'),
  getSession: (id: string) => request<Session>('GET', `/sessions/${id}`),
  updateSession: (id: string, patch: Partial<CreateSessionRequest>) =>
    request<Session>('PATCH', `/sessions/${id}`, patch),
  reorderPages: (id: string, pageIds: string[]) =>
    request<{ reordered: boolean; page_count: number }>('PATCH', `/sessions/${id}/pages/reorder`, {
      page_ids: pageIds,
    }),
  deleteSession: (id: string) => request<void>('DELETE', `/sessions/${id}`),
  addPages: (id: string, files: File[], sequenceStart?: number) => {
    const form = new FormData();
    files.forEach((f) => form.append('files', f));
    if (sequenceStart != null) form.append('sequence_start', String(sequenceStart));
    return request<{ added: unknown[] }>('POST', `/sessions/${id}/pages`, form);
  },

  // --- Pipeline ---
  process: (id: string, stages?: PipelineStage[], options?: Record<string, unknown>) =>
    request<{ run_id: string; status: string }>('POST', `/sessions/${id}/process`, {
      stages,
      options,
    }),
  runStage: (id: string, stage: PipelineStage) =>
    request<{ run_id: string; stage: string; status: string }>(
      'POST',
      `/sessions/${id}/stages/${stage}`,
    ),
  getRun: (id: string, runId: string) =>
    request<PipelineRun>('GET', `/sessions/${id}/runs/${runId}`),
  cancelRun: (id: string, runId: string) =>
    request<{ cancelled: boolean }>('POST', `/sessions/${id}/runs/${runId}/cancel`),

  // --- Review ---
  getReview: (id: string, pageId: string) =>
    request<ReviewPayload>('GET', `/sessions/${id}/pages/${pageId}/review`),
  correctBlock: (id: string, pageId: string, blockId: string, correctedContent: string | null) =>
    request('PATCH', `/sessions/${id}/pages/${pageId}/blocks/${blockId}`, {
      corrected_content: correctedContent,
      review_flag: false,
    }),
  setDiagramDecision: (id: string, pageId: string, blockId: string, decision: string) =>
    request('PATCH', `/sessions/${id}/pages/${pageId}/diagrams/${blockId}`, {
      review_decision: decision,
    }),

  // --- Export ---
  exportSession: (id: string, exportMode: string, vaultSubfolder?: string | null) =>
    request<{ export_run_id: string; status: string; vault_path: string }>(
      'POST',
      `/sessions/${id}/export`,
      { export_mode: exportMode, vault_subfolder: vaultSubfolder ?? null },
    ),
  getExportStatus: (id: string) => request('GET', `/sessions/${id}/export/status`),

  // --- Config ---
  getConfig: () => request<AppConfig>('GET', '/config'),
  putConfig: (config: AppConfig) => request<AppConfig>('PUT', '/config', config),
  patchConfig: (patch: Partial<AppConfig>) => request<AppConfig>('PATCH', '/config', patch),
  validateVault: () => request<VaultValidation>('GET', '/config/vault/validate'),
  vlmStatus: () => request<Record<string, unknown>>('GET', '/config/vlm/status'),

  // --- Health ---
  health: () => request<{ status: string }>('GET', '/health'),
};

/** Open the pipeline progress WebSocket for a session. Returns a close function. */
export async function connectProgress(
  sessionId: string,
  onEvent: (event: ProgressEvent) => void,
): Promise<() => void> {
  const port = await resolvePort();
  const ws = new WebSocket(`ws://127.0.0.1:${port}${API_PREFIX}/sessions/${sessionId}/progress`);
  ws.onmessage = (msg) => {
    try {
      onEvent(JSON.parse(msg.data) as ProgressEvent);
    } catch {
      /* ignore malformed frames */
    }
  };
  return () => ws.close();
}

export { ApiError };
