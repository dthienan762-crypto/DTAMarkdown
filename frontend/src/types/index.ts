export type PipelineType = 'auto' | 'vision_ocr' | 'voice_stt' | 'text_normalize';

export type JobStatus = 'QUEUED' | 'PROCESSING' | 'STREAMING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export interface ConversionOptions {
  extract_tables?: boolean;
  extract_math?: boolean;
  generate_toc?: boolean;
  extract_tags?: boolean;
  timestamp_silence_threshold?: number;
  preferred_engine?: 'auto' | 'gemini' | 'local_onnx' | 'pymupdf_fast';
}

export interface ConversionMetadata {
  word_count?: number;
  character_count?: number;
  estimated_read_time?: string;
  duration_ms?: number;
  engine_used?: string;
  tags?: string[];
  warnings?: string[];
  toc?: string;
}

export interface ConversionResult {
  job_id?: string;
  success: boolean;
  pipeline: PipelineType;
  markdown: string;
  metadata?: ConversionMetadata;
  warnings?: string[];
  duration_ms: number;
}

export interface JobCreatedResponse {
  job_id: string;
  status: JobStatus;
  pipeline: PipelineType;
  created_at: string;
  stream_url: string;
}

export interface ErrorResponse {
  code: string;
  message: string;
  details?: Record<string, unknown> | null;
  timestamp: string;
}

export interface JobDetailResponse {
  job_id: string;
  status: JobStatus;
  pipeline: PipelineType;
  progress?: number;
  created_at: string;
  completed_at?: string | null;
  result?: ConversionResult | null;
  error?: ErrorResponse | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  uptime_seconds: number;
  engines_available: {
    pymupdf_fast?: boolean;
    gemini_vision?: boolean;
    rapidocr_onnx?: boolean;
    faster_whisper?: boolean;
    speech_recognition?: boolean;
  };
  active_jobs: number;
}

// WebSocket Frames
export interface WebSocketStatusFrame {
  event: 'status';
  job_id: string;
  stage: string;
  progress: number;
  message: string;
  timestamp: string;
}

export interface WebSocketChunkFrame {
  event: 'chunk';
  job_id: string;
  delta: string;
  index: number;
  timestamp: string;
}

export interface WebSocketCompleteFrame {
  event: 'complete';
  job_id: string;
  markdown: string;
  metadata: ConversionMetadata;
  timestamp: string;
}

export interface WebSocketErrorFrame {
  event: 'error';
  job_id: string;
  code: string;
  message: string;
  recoverable: boolean;
  timestamp: string;
}

export type WebSocketFrame =
  | WebSocketStatusFrame
  | WebSocketChunkFrame
  | WebSocketCompleteFrame
  | WebSocketErrorFrame;

// Client UI Queue Item
export interface QueueItem {
  id: string; // UUID or temporary client id
  name: string;
  size: number;
  type: string;
  pipeline: PipelineType;
  status: JobStatus;
  progress: number;
  stage?: string;
  markdown?: string;
  metadata?: ConversionMetadata;
  error?: string;
  file?: File;
  controller?: AbortController;
  createdAt: number;
}

// Toast notification
export interface ToastMessage {
  id: string;
  title: string;
  description?: string;
  type: 'info' | 'success' | 'warning' | 'error';
  duration?: number;
}
