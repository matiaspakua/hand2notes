// TypeScript mirrors of the backend contracts (see specs/.../contracts/).

export type SessionStatus = 'created' | 'processing' | 'review' | 'exported' | 'failed';
export type ReviewStatus = 'pending' | 'in_review' | 'approved' | 'flagged';
export type ExportMode = 'overwrite' | 'versioned' | 'merge';
export type VLMRuntime = 'llamacpp' | 'ollama';
export type RunStatus = 'running' | 'completed' | 'failed' | 'cancelled';
export type DiagramDecision = 'pending' | 'approved' | 'rejected' | 'deferred';

export type PipelineStage =
  | 'preprocess'
  | 'detect_layout'
  | 'recognize_text'
  | 'reconstruct_structure'
  | 'detect_diagrams'
  | 'generate_output';

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Block {
  id: string;
  block_type: string;
  reading_order: number;
  bbox: BoundingBox;
  confidence: number;
  review_flag: boolean;
  content: string | null;
  corrected_content: string | null;
  visual_semantics: Record<string, unknown> | null;
}

export interface Page {
  id: string;
  sequence: number;
  source_path: string;
  width_px: number;
  height_px: number;
  pipeline_stage: string;
  review_status: ReviewStatus;
}

export interface Session {
  id: string;
  name: string;
  notebook: string;
  topic: string | null;
  status: SessionStatus;
  created_at: string;
  pages: Page[];
  tags: string[];
}

export interface CreateSessionRequest {
  name: string;
  notebook: string;
  topic?: string | null;
  tags?: string[];
  export_mode?: ExportMode;
}

export interface PipelineRun {
  id: string;
  session_id: string;
  stage: string;
  started_at: string;
  completed_at: string | null;
  status: RunStatus;
  error: string | null;
  metrics: Record<string, number>;
  progress?: { current_page: number; total_pages: number; percent: number };
}

export interface RunStageTiming {
  stage: string;
  elapsed_s: number;
  metrics: Record<string, number>;
}

export interface ProgressEvent {
  event:
    | 'stage_started'
    | 'stage_completed'
    | 'page_layout_detected'
    | 'run_metrics'
    | 'run_completed'
    | 'run_failed'
    | 'run_cancelled';
  stage?: string;
  page_id?: string;
  page_index?: number;
  total_pages?: number;
  page_width?: number;
  page_height?: number;
  blocks?: {
    block_type: string;
    bbox: BoundingBox;
    confidence: number;
  }[];
  metrics?: Record<string, number>;
  error?: string;
  message?: string;
  progress_percent?: number;
  timestamp?: string;
  // run_metrics payload
  total_elapsed_s?: number;
  stage_count?: number;
  slowest_stage?: string | null;
  slowest_stage_s?: number;
  stages?: RunStageTiming[];
}

export interface ReviewPayload {
  page_id: string;
  sequence: number;
  original_image_url: string;
  preprocessed_image_url: string;
  blocks: Block[];
  markdown_preview: string;
  diagram_previews: DiagramPreview[];
  overall_confidence: number;
  review_status: ReviewStatus;
}

export interface DiagramPreview {
  block_id: string;
  diagram_type: string;
  crop_url: string;
  generated_source_url: string | null;
  reconstruction_confidence: number;
  review_decision: DiagramDecision;
}

export interface AppConfig {
  vault_root: string | null;
  folder_template: string;
  export_mode: ExportMode;
  default_notebook: string | null;
  vlm_runtime: VLMRuntime;
  vlm_model: string;
  ocr_languages: string[];
  confidence_threshold: number;
  front_matter_fields: Record<string, string>;
}

export interface VaultValidation {
  valid: boolean;
  vault_root: string;
  writable?: boolean;
  existing_notes_count?: number;
  error?: string;
}
