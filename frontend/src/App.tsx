import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Header, ViewMode } from './components/Header';
import { IngestionZone } from './components/IngestionZone';
import { LiveEditor } from './components/LiveEditor';
import { ExportBar } from './components/ExportBar';
import { ToastContainer } from './components/Toast';
import { QueueItem, ToastMessage, HealthResponse, PipelineType } from './types';
import { useClipboardPaste } from './hooks/useClipboardPaste';
import { useWebSocketStream } from './hooks/useWebSocketStream';
import {
  Locale,
  DEFAULT_MARKDOWN_VI,
  DEFAULT_MARKDOWN_EN,
  translations,
} from './lib/i18n';
import {
  uploadFileForConversion,
  convertRawText,
  checkServerHealth,
} from './lib/api';
import { clientNormalizeText } from './lib/clientNormalizer';
import { extractPdfTextFromFile } from './lib/pdfExtractor';

export const App: React.FC = () => {
  const [locale, setLocale] = useState<Locale>(() => {
    try {
      const saved = localStorage.getItem('dtamarkdown_locale');
      if (saved === 'vi' || saved === 'en') return saved;
    } catch {
      // fallback
    }
    return 'vi';
  });

  const [markdown, setMarkdown] = useState<string>(
    locale === 'vi' ? DEFAULT_MARKDOWN_VI : DEFAULT_MARKDOWN_EN
  );
  const [viewMode, setViewMode] = useState<ViewMode>('split');
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [activeItemId, setActiveItemId] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [serverHealth, setServerHealth] = useState<HealthResponse | null>(null);
  const [isHealthChecking, setIsHealthChecking] = useState<boolean>(true);
  const isBackendConnected = Boolean(serverHealth);

  const activeJobIdRef = useRef<string | null>(null);
  const t = translations[locale];

  // Language switcher handler
  const handleLocaleChange = useCallback((newLocale: Locale) => {
    setLocale(newLocale);
    try {
      localStorage.setItem('dtamarkdown_locale', newLocale);
    } catch {
      // ignore
    }
  }, []);

  // Template loader handler
  const handleLoadTemplate = useCallback((templateLocale: Locale) => {
    if (templateLocale === 'vi') {
      setMarkdown(DEFAULT_MARKDOWN_VI);
      addToast(translations[templateLocale].templateVi, 'Đã tải mẫu tài liệu tiếng Việt đầy đủ', 'info');
    } else {
      setMarkdown(DEFAULT_MARKDOWN_EN);
      addToast(translations[templateLocale].templateEn, 'Loaded complete English template', 'info');
    }
    setActiveItemId(null);
  }, []);

  // Toast helper
  const addToast = useCallback(
    (
      title: string,
      description?: string,
      type: 'success' | 'info' | 'warning' | 'error' = 'info',
      duration = 4000
    ) => {
      const id = `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      setToasts((prev) => [...prev, { id, title, description, type, duration }]);

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    },
    []
  );

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Check backend server health
  useEffect(() => {
    let mounted = true;
    checkServerHealth()
      .then((health) => {
        if (mounted) {
          setServerHealth(health);
          setIsHealthChecking(false);
        }
      })
      .catch(() => {
        if (mounted) {
          setServerHealth(null);
          setIsHealthChecking(false);
        }
      });

    return () => {
      mounted = false;
    };
  }, []);

  // WebSocket streaming handler
  const {
    startStream,
    cancelStream,
    isStreaming,
  } = useWebSocketStream({
    onChunk: (delta) => {
      setMarkdown((prev) => prev + delta);
    },
    onStatus: (stage, progress, message) => {
      if (activeJobIdRef.current) {
        setQueue((prev) =>
          prev.map((item) =>
            item.id === activeJobIdRef.current
              ? { ...item, stage: message || stage, progress }
              : item
          )
        );
      }
    },
    onComplete: (finalMd, metadata) => {
      if (activeJobIdRef.current) {
        const jobId = activeJobIdRef.current;
        setQueue((prev) =>
          prev.map((item) =>
            item.id === jobId
              ? {
                  ...item,
                  status: 'COMPLETED',
                  progress: 100,
                  stage: t.statusReady,
                  markdown: finalMd,
                  metadata,
                }
              : item
          )
        );
      }
      setMarkdown(finalMd);
      addToast(t.toastConversionComplete, t.toastConversionCompleteDesc, 'success');
    },
    onError: (code, message) => {
      if (activeJobIdRef.current) {
        const jobId = activeJobIdRef.current;
        setQueue((prev) =>
          prev.map((item) =>
            item.id === jobId
              ? { ...item, status: 'FAILED', error: message, stage: t.statusFailed }
              : item
          )
        );
      }
      addToast('Conversion error', `[${code}] ${message}`, 'error', 6000);
    },
  });

  // Convert an uploaded file or audio blob
  const processConversion = useCallback(
    async (file: File | Blob, name: string, pipeline: PipelineType = 'auto') => {
      const tempId = `item-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`;
      const controller = new AbortController();

      const newItem: QueueItem = {
        id: tempId,
        name,
        size: file.size,
        type: file.type,
        pipeline,
        status: 'QUEUED',
        progress: 10,
        stage: t.statusUploading,
        file: file instanceof File ? file : undefined,
        controller,
        createdAt: Date.now(),
      };

      setQueue((prev) => [newItem, ...prev]);
      setActiveItemId(tempId);

      try {
        const created = await uploadFileForConversion(
          file,
          name,
          pipeline,
          {
            extract_tables: true,
            extract_math: true,
            generate_toc: true,
            extract_tags: true,
          },
          controller.signal
        );

        const realJobId = created.job_id;
        activeJobIdRef.current = realJobId;

        // Replace tempId with realJobId
        setQueue((prev) =>
          prev.map((item) =>
            item.id === tempId
              ? {
                  ...item,
                  id: realJobId,
                  status: created.status,
                  stage: t.statusConverting,
                  progress: 25,
                }
              : item
          )
        );
        setActiveItemId(realJobId);

        // Clear editor for streaming content
        setMarkdown('');

        // Start WebSocket real-time stream
        startStream(realJobId);
      } catch (err: unknown) {
        // Fallback for PDF documents when backend is offline or on Vercel
        if (file instanceof File && file.name.toLowerCase().endsWith('.pdf')) {
          try {
            const extractedPdfText = await extractPdfTextFromFile(file);
            if (extractedPdfText && extractedPdfText.trim().length > 0) {
              const normalized = clientNormalizeText(extractedPdfText, {
                extract_tables: true,
                extract_math: true,
                generate_toc: true,
                extract_tags: true,
              });
              setMarkdown(normalized.markdown);
              setQueue((prev) =>
                prev.map((item) =>
                  item.id === tempId
                    ? {
                        ...item,
                        status: 'COMPLETED',
                        progress: 100,
                        stage: t.statusReady,
                        markdown: normalized.markdown,
                        metadata: normalized.metadata,
                      }
                    : item
                )
              );
              addToast(
                locale === 'vi' ? 'Chuyển đổi PDF thành công' : 'PDF Converted',
                locale === 'vi'
                  ? `Đã trích xuất văn bản, bảng biểu và công thức từ ${file.name} sang Markdown GFM.`
                  : `Successfully extracted and normalized ${file.name} into GFM Markdown.`,
                'success'
              );
              return;
            }
          } catch (pdfErr) {
            console.warn('Browser-native PDF extraction error:', pdfErr);
          }
        }

        let msg = err instanceof Error ? err.message : 'Upload failed';
        if (msg.includes('500') || msg.includes('404') || msg.includes('Failed to fetch') || msg.includes('Không thể kết nối') || msg.includes('ERR_CONNECTION')) {
          msg = locale === 'vi'
            ? 'Tài liệu cần kết nối máy chủ Python Backend (Port 8000) để kích hoạt Vision OCR cho ảnh scan hoặc nhận dạng giọng nói. Chế độ Web hiện tại hỗ trợ 100% chuẩn hóa văn bản, tài liệu PDF số, bảng biểu và công thức KaTeX.'
            : 'Scanned image OCR and audio require the Python Backend (Port 8000). Digital PDFs, tables, text, and KaTeX math are 100% supported offline.';
        }
        setQueue((prev) =>
          prev.map((item) =>
            item.id === tempId
              ? { ...item, status: 'FAILED', error: msg, stage: t.statusFailed }
              : item
          )
        );
        addToast(locale === 'vi' ? 'Thông báo xử lý' : 'Processing Notice', msg, 'info', 7000);
      }
    },
    [addToast, startStream, t, locale]
  );

  // Ingestion: Text or HTML normalization
  const handleTextPasteTrigger = useCallback(
    async (rawText: string, isHtml: boolean) => {
      const tempId = `text-${Date.now()}`;
      const newItem: QueueItem = {
        id: tempId,
        name: isHtml ? 'pasted-table.html' : 'pasted-text.txt',
        size: rawText.length,
        type: isHtml ? 'text/html' : 'text/plain',
        pipeline: 'text_normalize',
        status: 'PROCESSING',
        progress: 30,
        stage: t.statusConverting,
        createdAt: Date.now(),
      };

      setQueue((prev) => [newItem, ...prev]);
      setActiveItemId(tempId);
      addToast(
        isHtml ? (locale === 'vi' ? 'Đã nhận dạng bảng HTML' : 'HTML table detected') : (locale === 'vi' ? 'Đã nhận dạng văn bản' : 'Raw text detected'),
        locale === 'vi' ? 'Đang chuẩn hóa thành Markdown chuẩn GFM...' : 'Normalizing to pristine GFM Markdown...',
        'info'
      );

      try {
        const result = await convertRawText(rawText, 'text_normalize', {
          extract_tables: true,
          extract_math: true,
          generate_toc: true,
          extract_tags: true,
        });

        setMarkdown(result.markdown);
        setQueue((prev) =>
          prev.map((item) =>
            item.id === tempId
              ? {
                  ...item,
                  status: 'COMPLETED',
                  progress: 100,
                  stage: t.statusReady,
                  markdown: result.markdown,
                  metadata: result.metadata,
                }
              : item
          )
        );
        addToast(t.toastTextNormalized, t.toastTextNormalizedDesc, 'success');
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Normalization failed';
        setQueue((prev) =>
          prev.map((item) =>
            item.id === tempId
              ? { ...item, status: 'FAILED', error: msg, stage: t.statusFailed }
              : item
          )
        );
        addToast(locale === 'vi' ? 'Chuẩn hóa thất bại' : 'Text conversion failed', msg, 'error');
      }
    },
    [addToast, t, locale]
  );

  // Ingestion: Audio voice recording
  const handleAudioRecorded = useCallback(
    (blob: Blob, name: string) => {
      addToast(t.toastVoiceCaptured, t.toastVoiceCapturedDesc, 'info');
      processConversion(blob, name, 'voice_stt');
    },
    [addToast, processConversion, t]
  );

  // Ingestion: Drag-and-drop or file browser with client-side text file reading
  const handleFilesSelected = useCallback(
    (files: File[]) => {
      files.forEach(async (file) => {
        // Enforce 200MB maximum file size limit
        if (file.size > 200 * 1024 * 1024) {
          addToast(
            locale === 'vi' ? 'Tệp vượt quá 200MB' : 'File Exceeds 200MB',
            locale === 'vi'
              ? `Tệp ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)}MB) vượt quá dung lượng tối đa 200MB.`
              : `File ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)}MB) exceeds maximum limit of 200MB.`,
            'error'
          );
          return;
        }

        const ext = file.name.split('.').pop()?.toLowerCase();
        // If file is text, html, or markdown, read directly in browser
        if (['html', 'htm', 'txt', 'md', 'csv', 'json'].includes(ext || '')) {
          try {
            const rawContent = await file.text();
            await handleTextPasteTrigger(rawContent, ext === 'html' || ext === 'htm');
            return;
          } catch {
            // fallback to processConversion
          }
        }

        // Fast browser-native PDF extraction when backend is not connected
        if (ext === 'pdf' && !isBackendConnected) {
          try {
            const rawPdfText = await extractPdfTextFromFile(file);
            if (rawPdfText && rawPdfText.trim().length > 0) {
              await handleTextPasteTrigger(rawPdfText, false);
              return;
            }
          } catch {
            // fallback to processConversion
          }
        }

        let pipeline: PipelineType = 'auto';
        if (['wav', 'mp3', 'm4a', 'ogg'].includes(ext || '')) {
          pipeline = 'voice_stt';
        } else if (['png', 'jpg', 'jpeg', 'webp', 'tiff', 'pdf'].includes(ext || '')) {
          pipeline = 'vision_ocr';
        } else {
          pipeline = 'text_normalize';
        }
        processConversion(file, file.name, pipeline);
      });
    },
    [handleTextPasteTrigger, processConversion, isBackendConnected, addToast, locale]
  );

  // Global Clipboard Paste Hook (Ctrl+V)
  useClipboardPaste({
    onImagePasted: (file) => {
      addToast(
        locale === 'vi' ? 'Hình ảnh từ Clipboard' : 'Image detected from clipboard',
        locale === 'vi' ? 'Bắt đầu Vision OCR trích xuất bảng biểu & công thức...' : 'Starting Vision OCR table & math extraction...',
        'info'
      );
      processConversion(file, file.name, 'vision_ocr');
    },
    onTextPasted: (text, isHtml) => {
      handleTextPasteTrigger(text, isHtml);
    },
  });

  // Global Keyboard Shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+S / Cmd+S -> Export .md
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault();
        const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'document.md';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        addToast(t.toastSavedMd, t.toastSavedMdDesc, 'success');
      }

      // Ctrl+Shift+E / Cmd+Shift+E -> Trigger PDF
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'e') {
        e.preventDefault();
        window.print();
      }

      // Alt+Z -> Toggle Split / Editor / Preview
      if (e.altKey && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        setViewMode((current) => {
          if (current === 'split') return 'editor';
          if (current === 'editor') return 'preview';
          return 'split';
        });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [markdown, addToast, t]);

  // Queue actions
  const handleSelectQueueItem = (item: QueueItem) => {
    setActiveItemId(item.id);
    if (item.markdown) {
      setMarkdown(item.markdown);
      addToast(locale === 'vi' ? 'Đã nạp tài liệu' : 'Loaded document', item.name, 'info', 2000);
    }
  };

  const handleRemoveQueueItem = (id: string) => {
    setQueue((prev) => prev.filter((item) => item.id !== id));
    if (activeItemId === id) {
      setActiveItemId(null);
    }
  };

  const handleCancelQueueItem = (id: string) => {
    const item = queue.find((i) => i.id === id);
    if (item?.controller) {
      item.controller.abort();
    }
    if (activeJobIdRef.current === id) {
      cancelStream();
    }
    setQueue((prev) =>
      prev.map((i) => (i.id === id ? { ...i, status: 'CANCELLED', stage: t.statusCancelled } : i))
    );
  };

  const handleResetDocument = () => {
    setMarkdown('');
    setActiveItemId(null);
    addToast(
      locale === 'vi' ? 'Đã tạo tài liệu mới' : 'New document created',
      locale === 'vi' ? 'Sẵn sàng soạn thảo nội dung' : 'Ready for new content',
      'info',
      2000
    );
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 antialiased transition-colors duration-200">
      {/* Toast notifications */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      {/* Header Bar */}
      <Header
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onResetDocument={handleResetDocument}
        onLoadTemplate={handleLoadTemplate}
        locale={locale}
        onLocaleChange={handleLocaleChange}
        serverHealth={serverHealth}
        isHealthChecking={isHealthChecking}
      />

      {/* Ingestion Zone Strip */}
      <div className="IngestionZone-container shrink-0">
        <IngestionZone
          queue={queue}
          activeItemId={activeItemId}
          locale={locale}
          onFilesSelected={handleFilesSelected}
          onAudioRecorded={handleAudioRecorded}
          onTextPasteTrigger={handleTextPasteTrigger}
          onSelectQueueItem={handleSelectQueueItem}
          onRemoveQueueItem={handleRemoveQueueItem}
          onCancelQueueItem={handleCancelQueueItem}
        />
      </div>

      {/* Split-Screen Live Editor */}
      <main className="flex-1 flex min-h-0 relative">
        <LiveEditor
          content={markdown}
          onChange={setMarkdown}
          viewMode={viewMode}
          locale={locale}
          isStreaming={isStreaming}
        />
      </main>

      {/* Status & Export Dock */}
      <ExportBar
        content={markdown}
        isBackendConnected={Boolean(serverHealth)}
        locale={locale}
        onShowToast={addToast}
      />
    </div>
  );
};

export default App;
