import {
  ConversionOptions,
  ConversionResult,
  JobCreatedResponse,
  JobDetailResponse,
  HealthResponse,
  PipelineType,
} from '../types';

const API_BASE = '/api/v1';

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

  const response = await fetch(`${API_BASE}/convert/file`, {
    method: 'POST',
    body: formData,
    signal,
  });

  if (!response.ok) {
    let errorMsg = `Upload failed with HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.message) {
        errorMsg = errJson.message;
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
  const response = await fetch(`${API_BASE}/convert/text`, {
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
  });

  if (!response.ok) {
    let errorMsg = `Text conversion failed with HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.message) {
        errorMsg = errJson.message;
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
  const response = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}`, {
    method: 'GET',
    signal,
  });

  if (!response.ok) {
    let errorMsg = `Failed to get job ${jobId} (HTTP ${response.status})`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.message) {
        errorMsg = errJson.message;
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
  const response = await fetch(`${API_BASE}/export/pdf`, {
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
  });

  if (!response.ok) {
    let errorMsg = `PDF export failed with HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson && errJson.message) {
        errorMsg = errJson.message;
      }
    } catch {
      // ignore
    }
    throw new Error(errorMsg);
  }

  return response.blob();
}

export async function checkServerHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`, {
    method: 'GET',
    signal,
  });

  if (!response.ok) {
    throw new Error(`Health check returned HTTP ${response.status}`);
  }

  return response.json();
}
