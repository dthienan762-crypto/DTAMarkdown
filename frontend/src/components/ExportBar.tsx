import React, { useState, useMemo } from 'react';
import {
  Copy,
  Check,
  Download,
  FileCode,
  Printer,
  ChevronDown,
  FileText,
  Clock,
} from 'lucide-react';
import { exportMarkdownToPdf } from '../lib/api';
import { Locale, translations } from '../lib/i18n';

interface ExportBarProps {
  content: string;
  isBackendConnected: boolean;
  locale?: Locale;
  onShowToast: (title: string, description?: string, type?: 'success' | 'info' | 'error') => void;
}

export const ExportBar: React.FC<ExportBarProps> = ({
  content,
  isBackendConnected,
  locale = 'vi',
  onShowToast,
}) => {
  const [copied, setCopied] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [showPdfMenu, setShowPdfMenu] = useState(false);

  const t = translations[locale];

  // Live document statistics
  const stats = useMemo(() => {
    const chars = content.length;
    const words = content.trim().length === 0 ? 0 : content.trim().split(/\s+/).length;
    const readingTimeMinutes = Math.max(1, Math.ceil(words / 200));
    return {
      chars,
      words,
      readingTime: `${readingTimeMinutes} ${t.readingTime}`,
    };
  }, [content, t.readingTime]);

  // Extract a sanitized title from first H1 or first non-empty line
  const documentTitle = useMemo(() => {
    const lines = content.split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('# ')) {
        return trimmed.replace('# ', '').trim();
      }
      if (trimmed.length > 0 && !trimmed.startsWith('```') && !trimmed.startsWith('---')) {
        return trimmed.slice(0, 40).trim();
      }
    }
    return locale === 'vi' ? 'tai-lieu' : 'document';
  }, [content, locale]);

  const sanitizedFileName = useMemo(() => {
    return (
      documentTitle
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .replace(/đ/g, 'd')
        .replace(/[^a-z0-9_-]/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '') || (locale === 'vi' ? 'tai-lieu' : 'document')
    );
  }, [documentTitle, locale]);

  // 1. One-click copy
  const handleCopyMarkdown = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      onShowToast(t.toastCopied, t.toastCopiedDesc, 'success');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      onShowToast('Copy failed', 'Could not access clipboard', 'error');
    }
  };

  // 2. Download .md
  const handleDownloadMd = () => {
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${sanitizedFileName}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    onShowToast(t.toastSavedMd, `${sanitizedFileName}.md`, 'success');
  };

  // 3. Export standalone styled HTML with full Vietnamese font support
  const handleExportHtml = () => {
    const htmlTemplate = `<!DOCTYPE html>
<html lang="${locale}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${documentTitle}</title>
  <!-- KaTeX CSS for math formulas -->
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/katex.min.css">
  <style>
    :root {
      color-scheme: light dark;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      line-height: 1.7;
      max-width: 880px;
      margin: 40px auto;
      padding: 0 24px;
      color: #0f172a;
      background: #ffffff;
      text-rendering: optimizeLegibility;
      -webkit-font-smoothing: antialiased;
    }
    @media (prefers-color-scheme: dark) {
      body {
        background: #020617;
        color: #f1f5f9;
      }
      table th { background: #0f172a; color: #f1f5f9; }
      table td { border-color: #1e293b; }
      pre { background: #0f172a; border-color: #1e293b; }
      code { background: #1e293b; color: #818cf8; }
      blockquote { background: #0f172a; color: #94a3b8; }
      h1, h2, h3 { color: #f8fafc; border-color: #1e293b; }
    }
    h1, h2, h3 { font-weight: 700; line-height: 1.3; margin-top: 1.6em; margin-bottom: 0.6em; }
    h1 { font-size: 2.1em; border-bottom: 2px solid #6366f1; padding-bottom: 0.4em; }
    h2 { font-size: 1.55em; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.35em; }
    h3 { font-size: 1.25em; }
    p { margin: 1.1em 0; }
    table { border-collapse: collapse; width: 100%; margin: 1.6em 0; border: 1px solid #cbd5e1; border-radius: 8px; overflow: hidden; }
    th, td { border: 1px solid #cbd5e1; padding: 10px 14px; text-align: left; font-size: 14px; }
    th { background: #f8fafc; font-weight: 600; }
    pre { background: #0f172a; color: #e2e8f0; padding: 18px; border-radius: 8px; overflow-x: auto; font-family: "JetBrains Mono", Consolas, monospace; font-size: 13px; border: 1px solid #334155; }
    code { font-family: "JetBrains Mono", Consolas, monospace; font-size: 0.9em; padding: 2px 6px; border-radius: 4px; background: #f1f5f9; color: #4338ca; }
    blockquote { border-left: 4px solid #6366f1; margin: 1.5em 0; padding: 10px 18px; background: #f8fafc; color: #64748b; font-style: italic; border-radius: 0 6px 6px 0; }
    ul, ol { padding-left: 24px; margin: 1em 0; }
    li { margin: 0.35em 0; }
    a { color: #4f46e5; text-decoration: underline; }
    @media print {
      body { max-width: 100%; margin: 0; padding: 15mm; color: #000; background: #fff; }
      pre, table, blockquote { break-inside: avoid; }
    }
  </style>
</head>
<body>
  <div id="content">
    <pre style="white-space: pre-wrap; font-family: inherit;">${content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')}</pre>
  </div>
</body>
</html>`;

    const blob = new Blob([htmlTemplate], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${sanitizedFileName}.html`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    onShowToast('HTML exported', `${sanitizedFileName}.html ready`, 'success');
  };

  // 4. Quick Browser Print / PDF
  const handleQuickPrint = () => {
    setShowPdfMenu(false);
    window.print();
  };

  // 5. Server-rendered PDF with Vietnamese Arial Unicode
  const handleServerPdf = async () => {
    setShowPdfMenu(false);
    setIsExportingPdf(true);
    try {
      const blob = await exportMarkdownToPdf(content, documentTitle);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${sanitizedFileName}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      onShowToast(t.toastPdfCompiled, `${sanitizedFileName}.pdf`, 'success');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Server PDF compilation failed';
      onShowToast('Falling back to Print', `${message}. Opening browser print dialog...`, 'info');
      window.print();
    } finally {
      setIsExportingPdf(false);
    }
  };

  return (
    <footer className="h-11 bg-slate-900/90 backdrop-blur-md border-t border-slate-800 px-3 sm:px-4 flex items-center justify-between text-xs select-none z-30 shrink-0">
      {/* Telemetry & Stats */}
      <div className="flex items-center gap-2 sm:gap-4 text-slate-400">
        <div className="flex items-center gap-1.5">
          <span
            className={`w-2 h-2 rounded-full ${
              isBackendConnected ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'
            }`}
          />
          <span className="font-mono text-[11px] text-slate-300">
            {isBackendConnected ? t.connected : t.offline}
          </span>
        </div>

        <div className="h-3 w-[1px] bg-slate-800 hidden sm:block" />

        <div className="hidden sm:flex items-center gap-3 text-slate-400 text-[11px]">
          <span>
            <strong className="text-slate-200 font-mono">{stats.words}</strong> {t.words}
          </span>
          <span>
            <strong className="text-slate-200 font-mono">{stats.chars}</strong> {t.chars}
          </span>
          <span className="flex items-center gap-1 text-slate-500">
            <Clock className="w-3 h-3" />
            {stats.readingTime}
          </span>
        </div>
      </div>

      {/* Export Action Buttons */}
      <div className="flex items-center gap-1.5 sm:gap-2">
        {/* Copy Markdown */}
        <button
          type="button"
          onClick={handleCopyMarkdown}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md font-medium transition-all ${
            copied
              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
              : 'bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/60'
          }`}
          title={t.copy}
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          <span className="hidden sm:inline">{copied ? t.copied : t.copy}</span>
        </button>

        {/* Download .md */}
        <button
          type="button"
          onClick={handleDownloadMd}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/60 transition-all"
          title={t.downloadMd}
        >
          <Download className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{t.downloadMd}</span>
        </button>

        {/* Export HTML */}
        <button
          type="button"
          onClick={handleExportHtml}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/60 transition-all"
          title={t.downloadHtml}
        >
          <FileCode className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{t.downloadHtml}</span>
        </button>

        {/* Export PDF with Dropdown */}
        <div className="relative">
          <div className="flex items-center rounded-md bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm transition-all overflow-hidden">
            <button
              type="button"
              onClick={handleQuickPrint}
              disabled={isExportingPdf}
              className="flex items-center gap-1.5 px-2.5 py-1 font-medium transition-colors"
              title="Print / Save as PDF (Ctrl+Shift+E)"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>{t.exportPdf}</span>
            </button>
            <button
              type="button"
              onClick={() => setShowPdfMenu((prev) => !prev)}
              className="px-1.5 py-1 bg-indigo-700 hover:bg-indigo-600 border-l border-indigo-500/50"
              title="PDF Options"
            >
              <ChevronDown className="w-3 h-3" />
            </button>
          </div>

          {/* PDF Dropdown Menu */}
          {showPdfMenu && (
            <div className="absolute right-0 bottom-full mb-1 w-52 bg-slate-900 border border-slate-800 rounded-lg shadow-xl py-1 text-xs text-slate-200 z-50 animate-in fade-in">
              <button
                type="button"
                onClick={handleQuickPrint}
                className="w-full text-left px-3 py-1.5 hover:bg-slate-800 flex items-center gap-2"
              >
                <Printer className="w-3.5 h-3.5 text-indigo-400" />
                <span>{t.quickPrint}</span>
              </button>
              <button
                type="button"
                onClick={handleServerPdf}
                disabled={isExportingPdf}
                className="w-full text-left px-3 py-1.5 hover:bg-slate-800 flex items-center gap-2 disabled:opacity-50"
              >
                <FileText className="w-3.5 h-3.5 text-emerald-400" />
                <span>{isExportingPdf ? 'Compiling...' : t.serverPdf}</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </footer>
  );
};

export default ExportBar;
