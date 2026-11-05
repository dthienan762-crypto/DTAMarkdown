import React, { useState, useRef, useCallback } from 'react';
import {
  UploadCloud,
  Mic,
  ClipboardPaste,
  FileText,
  FileCode,
  FileAudio,
  FileImage,
  CheckCircle2,
  AlertCircle,
  X,
  Loader2,
} from 'lucide-react';
import { QueueItem, PipelineType } from '../types';
import { WaveformVisualizer } from './WaveformVisualizer';
import { useAudioRecorder } from '../hooks/useAudioRecorder';
import { Locale, translations } from '../lib/i18n';

interface IngestionZoneProps {
  queue: QueueItem[];
  activeItemId: string | null;
  locale?: Locale;
  onFilesSelected: (files: File[]) => void;
  onAudioRecorded: (blob: Blob, name: string) => void;
  onTextPasteTrigger: (text: string, isHtml: boolean) => void;
  onSelectQueueItem: (item: QueueItem) => void;
  onRemoveQueueItem: (id: string) => void;
  onCancelQueueItem: (id: string) => void;
}

export const IngestionZone: React.FC<IngestionZoneProps> = ({
  queue,
  activeItemId,
  locale = 'vi',
  onFilesSelected,
  onAudioRecorded,
  onTextPasteTrigger,
  onSelectQueueItem,
  onRemoveQueueItem,
  onCancelQueueItem,
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [showPasteModal, setShowPasteModal] = useState(false);
  const [pastedText, setPastedText] = useState('');
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const t = translations[locale];

  const {
    isRecording,
    durationSeconds,
    analyserNode,
    startRecording,
    stopRecording,
    cancelRecording,
    error: recorderError,
  } = useAudioRecorder();

  // Drag & drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);

      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const filesArray = Array.from(e.dataTransfer.files);
        onFilesSelected(filesArray);
      }
    },
    [onFilesSelected]
  );

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const filesArray = Array.from(e.target.files);
      onFilesSelected(filesArray);
      e.target.value = '';
    }
  };

  // Audio recording handlers
  const handleStartVoice = async () => {
    try {
      await startRecording();
    } catch {
      // error handled in hook
    }
  };

  const handleStopVoice = async () => {
    const wavBlob = await stopRecording();
    if (wavBlob) {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      onAudioRecorded(wavBlob, `voice-recording-${timestamp}.wav`);
    }
  };

  const handleManualTextSubmit = () => {
    if (pastedText.trim().length > 0) {
      const isHtml = pastedText.includes('<table') || pastedText.includes('<html') || pastedText.includes('</');
      onTextPasteTrigger(pastedText, isHtml);
      setPastedText('');
      setShowPasteModal(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (name: string, pipeline: PipelineType) => {
    const ext = name.split('.').pop()?.toLowerCase();
    if (pipeline === 'voice_stt' || ['wav', 'mp3', 'm4a', 'ogg'].includes(ext || '')) {
      return <FileAudio className="w-4 h-4 text-purple-500 dark:text-purple-400" />;
    }
    if (pipeline === 'vision_ocr' || ['png', 'jpg', 'jpeg', 'webp', 'tiff', 'pdf'].includes(ext || '')) {
      return <FileImage className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />;
    }
    if (ext === 'html' || ext === 'htm') {
      return <FileCode className="w-4 h-4 text-amber-500 dark:text-amber-400" />;
    }
    return <FileText className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />;
  };

  return (
    <div className="bg-slate-50/90 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 p-3 sm:p-4 transition-colors duration-200">
      {/* If Audio Recording is active, show the 60 FPS Canvas Waveform dock */}
      {isRecording ? (
        <WaveformVisualizer
          analyserNode={analyserNode}
          durationSeconds={durationSeconds}
          onStop={handleStopVoice}
          onCancel={cancelRecording}
        />
      ) : (
        /* Standard Ingestion Zone Dropzone */
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`relative border-2 border-dashed rounded-xl p-3.5 sm:p-4 text-center transition-all duration-200 ${
            isDragOver
              ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/30 scale-[1.005] shadow-lg shadow-indigo-500/10'
              : 'border-slate-300 dark:border-slate-800 hover:border-slate-400 dark:hover:border-slate-700 bg-white/70 dark:bg-slate-950/40 shadow-sm'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.png,.jpg,.jpeg,.webp,.tiff,.wav,.mp3,.m4a,.ogg,.txt,.html,.htm,.md"
            onChange={handleFileInputChange}
            className="hidden"
          />

          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            {/* Left Prompt */}
            <div className="flex items-center gap-3.5 text-left">
              <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shrink-0">
                <UploadCloud className="w-5 h-5" />
              </div>
              <div>
                <div className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  {t.dragDropPrompt}{' '}
                  <kbd className="px-1.5 py-0.5 text-[11px] font-mono bg-slate-100 dark:bg-slate-800 text-indigo-600 dark:text-indigo-300 rounded border border-slate-300 dark:border-slate-700">
                    Ctrl+V
                  </kbd>
                </div>
                <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 flex flex-wrap items-center gap-1.5">
                  <span>{t.supportedFiles}</span>
                  <span className="text-slate-400 dark:text-slate-600">•</span>
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 dark:hover:text-indigo-300 font-medium underline underline-offset-2"
                  >
                    {t.browseFiles}
                  </button>
                </div>
              </div>
            </div>

            {/* Quick Actions (Mic, Paste Modal) */}
            <div className="flex items-center gap-2 shrink-0 w-full sm:w-auto justify-end">
              <button
                type="button"
                onClick={handleStartVoice}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 transition-all shadow-sm hover:border-indigo-500/50"
                title={t.recordVoiceTitle}
              >
                <Mic className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400" />
                <span>{t.recordVoice}</span>
              </button>

              <button
                type="button"
                onClick={() => setShowPasteModal(true)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 dark:text-slate-200 bg-white dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 border border-slate-300 dark:border-slate-700 transition-all shadow-sm hover:border-indigo-500/50"
                title={t.pasteTextHtmlTitle}
              >
                <ClipboardPaste className="w-3.5 h-3.5 text-emerald-500 dark:text-emerald-400" />
                <span>{t.pasteTextHtml}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {recorderError && (
        <div className="mt-2 text-xs text-rose-500 dark:text-rose-400 flex items-center gap-1.5">
          <AlertCircle className="w-3.5 h-3.5" />
          {t.micError}: {recorderError}
        </div>
      )}

      {/* Queue Card Tray (Horizontal / Multi-file display) */}
      {queue.length > 0 && (
        <div className="mt-3 flex items-center gap-2 overflow-x-auto pb-1 pt-1 scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-slate-800">
          {queue.map((item) => {
            const isActive = item.id === activeItemId;
            const isCompleted = item.status === 'COMPLETED';
            const isError = item.status === 'FAILED';
            const isProcessing =
              item.status === 'PROCESSING' ||
              item.status === 'STREAMING' ||
              item.status === 'QUEUED';

            return (
              <div
                key={item.id}
                onClick={() => isCompleted && onSelectQueueItem(item)}
                className={`relative shrink-0 flex items-center gap-3 px-3 py-2 rounded-lg border text-xs transition-all ${
                  isActive
                    ? 'bg-indigo-50 dark:bg-indigo-950/40 border-indigo-400 dark:border-indigo-500/60 shadow-sm'
                    : isCompleted
                    ? 'bg-white dark:bg-slate-950/60 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 cursor-pointer shadow-sm'
                    : isError
                    ? 'bg-rose-50 dark:bg-rose-950/20 border-rose-200 dark:border-rose-800/40'
                    : 'bg-white dark:bg-slate-950/60 border-slate-200 dark:border-slate-800'
                }`}
                style={{ minWidth: '220px', maxWidth: '280px' }}
              >
                {/* File Icon */}
                <div className="shrink-0">{getFileIcon(item.name, item.pipeline)}</div>

                {/* Info & Progress */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-1">
                    <span
                      className="font-medium text-slate-800 dark:text-slate-200 truncate"
                      title={item.name}
                    >
                      {item.name}
                    </span>
                    <span className="text-[10px] text-slate-500 shrink-0">
                      {formatFileSize(item.size)}
                    </span>
                  </div>

                  {/* Status Pill / Progress */}
                  <div className="mt-1 flex items-center justify-between gap-2 text-[10px]">
                    {isProcessing && (
                      <div className="flex items-center gap-1 text-indigo-600 dark:text-indigo-400">
                        <Loader2 className="w-2.5 h-2.5 animate-spin" />
                        <span>{item.stage || t.statusConverting}</span>
                      </div>
                    )}
                    {isCompleted && (
                      <div className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                        <CheckCircle2 className="w-2.5 h-2.5" />
                        <span>{t.statusReady}</span>
                      </div>
                    )}
                    {isError && (
                      <div className="flex items-center gap-1 text-rose-500 dark:text-rose-400 truncate">
                        <AlertCircle className="w-2.5 h-2.5 shrink-0" />
                        <span className="truncate">{item.error || t.statusFailed}</span>
                      </div>
                    )}

                    {isProcessing && (
                      <span className="font-mono text-slate-600 dark:text-slate-400">{item.progress}%</span>
                    )}
                  </div>

                  {/* Mini Progress Bar */}
                  {isProcessing && (
                    <div className="mt-1 h-1 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-indigo-500 transition-all duration-300"
                        style={{ width: `${Math.max(item.progress, 5)}%` }}
                      />
                    </div>
                  )}
                </div>

                {/* Cancel or Remove Action */}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (isProcessing) {
                      onCancelQueueItem(item.id);
                    } else {
                      onRemoveQueueItem(item.id);
                    }
                  }}
                  className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 p-0.5 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  title={isProcessing ? t.cancelRecording : 'Dismiss item'}
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Manual Paste Modal */}
      {showPasteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 dark:bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 max-w-lg w-full shadow-2xl">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                <ClipboardPaste className="w-4 h-4 text-indigo-500 dark:text-indigo-400" />
                {t.pasteModalTitle}
              </h3>
              <button
                type="button"
                onClick={() => setShowPasteModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">{t.pasteModalDesc}</p>
            <textarea
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              placeholder={t.pastePlaceholder}
              rows={8}
              className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg p-3 text-xs font-mono text-slate-900 dark:text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors"
            />
            <div className="mt-4 flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowPasteModal(false)}
                className="px-3 py-1.5 text-xs text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700"
              >
                {t.cancelButton}
              </button>
              <button
                type="button"
                onClick={handleManualTextSubmit}
                disabled={pastedText.trim().length === 0}
                className="px-4 py-1.5 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:pointer-events-none rounded-lg transition-all shadow-sm"
              >
                {t.normalizeButton}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default IngestionZone;
