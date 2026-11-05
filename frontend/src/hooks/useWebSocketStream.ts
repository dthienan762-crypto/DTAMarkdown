import { useState, useRef, useCallback, useEffect } from 'react';
import {
  JobStatus,
  ConversionMetadata,
  WebSocketFrame,
} from '../types';
import { getJobDetail } from '../lib/api';

export interface UseWebSocketStreamOptions {
  onChunk?: (delta: string, accumulated: string) => void;
  onStatus?: (stage: string, progress: number, message: string) => void;
  onComplete?: (markdown: string, metadata: ConversionMetadata) => void;
  onError?: (code: string, message: string) => void;
}

export interface UseWebSocketStreamReturn {
  jobId: string | null;
  status: JobStatus;
  progress: number;
  stage: string;
  message: string;
  streamedContent: string;
  metadata: ConversionMetadata | null;
  error: string | null;
  isStreaming: boolean;
  isPollingFallback: boolean;
  startStream: (jobId: string) => void;
  cancelStream: () => void;
  resetStream: () => void;
}

export function useWebSocketStream(
  options: UseWebSocketStreamOptions = {}
): UseWebSocketStreamReturn {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus>('QUEUED');
  const [progress, setProgress] = useState<number>(0);
  const [stage, setStage] = useState<string>('idle');
  const [message, setMessage] = useState<string>('');
  const [streamedContent, setStreamedContent] = useState<string>('');
  const [metadata, setMetadata] = useState<ConversionMetadata | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [isPollingFallback, setIsPollingFallback] = useState<boolean>(false);

  const wsRef = useRef<WebSocket | null>(null);
  const pollingIntervalRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const maxReconnectAttempts = 3;
  const contentAccumulatorRef = useRef<string>('');
  const activeJobIdRef = useRef<string | null>(null);
  const cancelledRef = useRef<boolean>(false);

  // Store options in ref to avoid stale closures
  const optionsRef = useRef(options);
  optionsRef.current = options;

  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }
  }, []);

  const closeWebSocket = useCallback(() => {
    if (wsRef.current) {
      // Avoid triggering onclose reconnect logic
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const resetStream = useCallback(() => {
    stopPolling();
    closeWebSocket();
    setJobId(null);
    activeJobIdRef.current = null;
    setStatus('QUEUED');
    setProgress(0);
    setStage('idle');
    setMessage('');
    setStreamedContent('');
    contentAccumulatorRef.current = '';
    setMetadata(null);
    setError(null);
    setIsStreaming(false);
    setIsPollingFallback(false);
    reconnectAttemptsRef.current = 0;
    cancelledRef.current = false;
  }, [stopPolling, closeWebSocket]);

  const startPolling = useCallback(
    (targetJobId: string) => {
      stopPolling();
      setIsPollingFallback(true);

      const poll = async () => {
        if (cancelledRef.current || activeJobIdRef.current !== targetJobId) {
          stopPolling();
          return;
        }

        try {
          const detail = await getJobDetail(targetJobId);
          setStatus(detail.status);
          if (detail.progress !== undefined) {
            setProgress(detail.progress);
          }

          if (detail.status === 'COMPLETED' && detail.result) {
            stopPolling();
            setIsStreaming(false);
            const finalMd = detail.result.markdown;
            setStreamedContent(finalMd);
            contentAccumulatorRef.current = finalMd;
            const meta = detail.result.metadata || {};
            setMetadata(meta);
            optionsRef.current.onComplete?.(finalMd, meta);
          } else if (detail.status === 'FAILED') {
            stopPolling();
            setIsStreaming(false);
            const errMsg = detail.error?.message || 'Job processing failed';
            setError(errMsg);
            optionsRef.current.onError?.(detail.error?.code || 'JOB_FAILED', errMsg);
          }
        } catch {
          // If poll fails, continue polling up to timeout
        }
      };

      // Poll immediately then interval
      poll();
      pollingIntervalRef.current = window.setInterval(poll, 1000);
    },
    [stopPolling]
  );

  const connectWebSocket = useCallback(
    (targetJobId: string) => {
      closeWebSocket();

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/api/v1/ws/stream/${encodeURIComponent(targetJobId)}`;

      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          reconnectAttemptsRef.current = 0;
          setIsStreaming(true);
          setIsPollingFallback(false);
          setStatus('STREAMING');
        };

        ws.onmessage = (event) => {
          try {
            const data: WebSocketFrame = JSON.parse(event.data);

            if (data.event === 'status') {
              setStage(data.stage);
              setProgress(data.progress);
              setMessage(data.message);
              optionsRef.current.onStatus?.(data.stage, data.progress, data.message);
            } else if (data.event === 'chunk') {
              contentAccumulatorRef.current += data.delta;
              const accumulated = contentAccumulatorRef.current;
              setStreamedContent(accumulated);
              optionsRef.current.onChunk?.(data.delta, accumulated);
            } else if (data.event === 'complete') {
              setIsStreaming(false);
              setStatus('COMPLETED');
              setProgress(100);
              const finalMd = data.markdown || contentAccumulatorRef.current;
              setStreamedContent(finalMd);
              contentAccumulatorRef.current = finalMd;
              setMetadata(data.metadata);
              optionsRef.current.onComplete?.(finalMd, data.metadata);
              closeWebSocket();
            } else if (data.event === 'error') {
              setIsStreaming(false);
              setStatus('FAILED');
              setError(data.message);
              optionsRef.current.onError?.(data.code, data.message);
              closeWebSocket();
            }
          } catch {
            // Non-JSON chunk, treat as raw text delta
            if (typeof event.data === 'string') {
              contentAccumulatorRef.current += event.data;
              setStreamedContent(contentAccumulatorRef.current);
              optionsRef.current.onChunk?.(event.data, contentAccumulatorRef.current);
            }
          }
        };

        ws.onerror = () => {
          // If WS error occurs, fall back to HTTP polling
          if (reconnectAttemptsRef.current < maxReconnectAttempts) {
            reconnectAttemptsRef.current += 1;
            setTimeout(() => {
              if (!cancelledRef.current && activeJobIdRef.current === targetJobId) {
                connectWebSocket(targetJobId);
              }
            }, 1000 * reconnectAttemptsRef.current);
          } else {
            // Fall back to polling
            startPolling(targetJobId);
          }
        };

        ws.onclose = (e) => {
          // If closed abnormally before completion, attempt fallback
          if (!cancelledRef.current && e.code !== 1000 && activeJobIdRef.current === targetJobId) {
            if (reconnectAttemptsRef.current < maxReconnectAttempts) {
              reconnectAttemptsRef.current += 1;
              setTimeout(() => {
                if (!cancelledRef.current && activeJobIdRef.current === targetJobId) {
                  connectWebSocket(targetJobId);
                }
              }, 1000 * reconnectAttemptsRef.current);
            } else {
              startPolling(targetJobId);
            }
          }
        };
      } catch {
        // Fallback to polling immediately
        startPolling(targetJobId);
      }
    },
    [closeWebSocket, startPolling]
  );

  const startStream = useCallback(
    (newJobId: string) => {
      resetStream();
      setJobId(newJobId);
      activeJobIdRef.current = newJobId;
      setIsStreaming(true);
      setStatus('PROCESSING');
      setProgress(5);
      connectWebSocket(newJobId);
    },
    [resetStream, connectWebSocket]
  );

  const cancelStream = useCallback(() => {
    cancelledRef.current = true;
    setStatus('CANCELLED');
    setIsStreaming(false);
    stopPolling();

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({ event: 'cancel', job_id: activeJobIdRef.current }));
      } catch {
        // ignore
      }
    }
    closeWebSocket();
  }, [stopPolling, closeWebSocket]);

  useEffect(() => {
    return () => {
      cancelledRef.current = true;
      stopPolling();
      closeWebSocket();
    };
  }, [stopPolling, closeWebSocket]);

  return {
    jobId,
    status,
    progress,
    stage,
    message,
    streamedContent,
    metadata,
    error,
    isStreaming,
    isPollingFallback,
    startStream,
    cancelStream,
    resetStream,
  };
}
