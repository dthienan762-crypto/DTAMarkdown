import {
  ConversionOptions,
  ConversionResult,
  JobCreatedResponse,
  JobDetailResponse,
  HealthResponse,
  PipelineType,
} from '../types';

// Read API_BASE from VITE_API_URL or default to /api/v1 (proxied by Vite or served directly)
const RAW_BASE = (import.meta.env.VITE_API_URL as string) || '/api/v1';
const API_BASE = RAW_BASE.replace(/\/+$/, '');

/**
 * Enhanced fetch wrapper with timeout, connection error detection, and meaningful messages.
 */
async function safeFetch(
  input: string,
  init?: RequestInit,
  timeoutMs = 60000
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let mergedSignal = controller.signal;
  if (init?.signal) {
    init.signal.addEventListener('abort', () => controller.abort());
  }

  try {
    const response = await fetch(input, {
      ...init,
      signal: mergedSignal,
    });
    return response;
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      if (init?.signal?.aborted) {
        throw new Error('Yêu cầu đã bị hủy (Request was cancelled).');
      }
      throw new Error(`Yêu cầu quá hạn (${timeoutMs / 1000}s). Vui lòng thử lại với tệp nhỏ hơn.`);
    }

    // Network / Connection Refused / CORS error
    const rawMsg = err instanceof Error ? err.message : String(err);
    if (
      rawMsg.includes('Failed to fetch') ||
      rawMsg.includes('NetworkError') ||
      rawMsg.includes('ERR_CONNECTION_REFUSED')
    ) {
      throw new Error(
        'Không thể kết nối đến máy chủ Backend (Port 8000/5000). Vui lòng đảm bảo server đang chạy: "python backend/run.py"'
      );
    }
    throw new Error(`Lỗi kết nối mạng: ${rawMsg}`);
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function uploadFileForConversion(
  file: File | Blob,
  fileName?: string,
  pipelineType: PipelineType = 'auto',
  options?: ConversionOptions,
  signal?: AbortSignal
): Promise<JobCreatedResponse> {
  const formData = new FormData();
  if (file instanceof File) {
    formData.append('file', file);
  } else {
    formData.append('file', file, fileName || 'recording.wav');
  }

  if (pipelineType && pipelineType !== 'auto') {
    formData.append('pipeline_type', pipelineType);
  }

  if (options) {
    formData.append('options_json', JSON.stringify(options));
  }

  const response = await safeFetch(
    `${API_BASE}/convert/file`,
    {
      method: 'POST',
      body: formData,
      signal,
    },
    120000 // 2 minutes for large OCR or audio
  );

  if (!response.ok) {
    let errorMsg = `Upload failed with HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson) {
        errorMsg = errJson.message || errJson.detail || errorMsg;
      }
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

export async function convertRawText(
  rawText: string,
  pipelineType: PipelineType = 'text_normalize',
  options?: ConversionOptions,
  signal?: AbortSignal
): Promise<ConversionResult> {
  const response = await safeFetch(
    `${API_BASE}/convert/text`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        raw_text: rawText,
        pipeline_type: pipelineType,
        options: options || {},
      }),
      signal,
    },
    30000
  );

  if (!response.ok) {
    let errorMsg = `Chuyển hóa thất bại (HTTP ${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson) {
        errorMsg = errJson.message || errJson.detail || errorMsg;
      }
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

export async function getJobDetail(
  jobId: string,
  signal?: AbortSignal
): Promise<JobDetailResponse> {
  const response = await safeFetch(
    `${API_BASE}/jobs/${encodeURIComponent(jobId)}`,
    {
      method: 'GET',
      signal,
    },
    15000
  );

  if (!response.ok) {
    let errorMsg = `Failed to get job ${jobId} (HTTP ${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson) {
        errorMsg = errJson.message || errJson.detail || errorMsg;
      }
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return response.json();
}

export async function exportMarkdownToPdf(
  markdown: string,
  title: string = 'Document',
  signal?: AbortSignal
): Promise<Blob> {
  const response = await safeFetch(
    `${API_BASE}/export/pdf`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        markdown,
        title,
        page_size: 'A4',
        orientation: 'portrait',
        include_styles: true,
      }),
      signal,
    },
    45000
  );

  if (!response.ok) {
    let errorMsg = `PDF export failed with HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson) {
        errorMsg = errJson.message || errJson.detail || errorMsg;
      }
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return response.blob();
}

export async function checkServerHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await safeFetch(
    `${API_BASE}/health`,
    {
      method: 'GET',
      signal,
    },
    5000
  );

  if (!response.ok) {
    throw new Error(`Health check returned HTTP ${response.status}`);
  }

  return response.json();
}
