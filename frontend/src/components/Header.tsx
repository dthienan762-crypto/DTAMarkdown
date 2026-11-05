import React, { useState } from 'react';
import {
  Columns,
  Code2,
  Eye,
  Sparkles,
  RotateCcw,
  BookOpen,
  ChevronDown,
} from 'lucide-react';
import { HealthResponse } from '../types';
import { Locale, translations } from '../lib/i18n';
import { ThemeToggle } from './ThemeToggle';

export type ViewMode = 'split' | 'editor' | 'preview';

interface HeaderProps {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  onResetDocument: () => void;
  onLoadTemplate: (template: Locale) => void;
  locale: Locale;
  onLocaleChange: (locale: Locale) => void;
  serverHealth: HealthResponse | null;
  isHealthChecking: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  viewMode,
  onViewModeChange,
  onResetDocument,
  onLoadTemplate,
  locale,
  onLocaleChange,
  serverHealth,
  isHealthChecking,
}) => {
  const [showTemplateMenu, setShowTemplateMenu] = useState(false);
  const t = translations[locale];
  const isHealthy = serverHealth?.status === 'HEALTHY' || !serverHealth;
  const availableEngines = serverHealth?.engines_available;

  return (
    <header className="h-14 bg-white/95 dark:bg-slate-900/90 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 px-3 sm:px-4 flex items-center justify-between select-none z-30 transition-colors duration-200">
      {/* Brand & Logo */}
      <div className="flex items-center gap-2.5 sm:gap-3 shrink-0">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-indigo-500/10 dark:bg-indigo-600/20 border border-indigo-500/30 dark:border-indigo-500/40 text-indigo-600 dark:text-indigo-400">
          <Sparkles className="w-4 h-4 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-1.5 sm:gap-2">
            <span className="font-bold text-sm sm:text-base tracking-tight text-slate-900 dark:text-slate-100">
              DTAMarkdown
            </span>
            <span className="text-[10px] sm:text-xs px-1.5 py-0.5 rounded bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-mono font-medium border border-indigo-200 dark:border-indigo-500/20">
              Studio
            </span>
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400 hidden lg:block">
            {t.brandSubtitle}
          </div>
        </div>
      </div>

      {/* Engine Status Indicators */}
      <div className="hidden 2xl:flex items-center gap-2 text-xs">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400">
          <span
            className={`w-2 h-2 rounded-full ${
              isHealthy ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'
            }`}
          />
          <span className="text-[11px] font-mono">
            {isHealthChecking
              ? t.serverChecking
              : serverHealth
              ? t.serverReady
              : t.standaloneMode}
          </span>
        </div>

        {availableEngines && (
          <div className="flex items-center gap-1 text-[10px]">
            {availableEngines.gemini_vision && (
              <span className="px-1.5 py-0.5 rounded bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800/40 text-indigo-600 dark:text-indigo-300">
                Gemini
              </span>
            )}
            {availableEngines.rapidocr_onnx && (
              <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                RapidOCR
              </span>
            )}
            {availableEngines.pymupdf_fast && (
              <span className="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                PyMuPDF
              </span>
            )}
          </div>
        )}
      </div>

      {/* Controls & Switchers */}
      <div className="flex items-center gap-1.5 sm:gap-2">
        {/* Theme Toggle (Light / Dark / System) */}
        <ThemeToggle locale={locale} />

        {/* Language Switcher */}
        <div className="flex items-center bg-slate-100 dark:bg-slate-950/80 p-0.5 rounded-lg border border-slate-200 dark:border-slate-800 text-xs">
          <button
            type="button"
            onClick={() => onLocaleChange('vi')}
            className={`flex items-center gap-1 px-2 py-1 rounded-md transition-all text-xs ${
              locale === 'vi'
                ? 'bg-indigo-600 text-white font-medium shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
            title="Chuyển sang Tiếng Việt"
          >
            <span>🇻🇳</span>
            <span className="hidden sm:inline">Tiếng Việt</span>
          </button>
          <button
            type="button"
            onClick={() => onLocaleChange('en')}
            className={`flex items-center gap-1 px-2 py-1 rounded-md transition-all text-xs ${
              locale === 'en'
                ? 'bg-indigo-600 text-white font-medium shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
            title="Switch to English"
          >
            <span>🇬🇧</span>
            <span className="hidden sm:inline">English</span>
          </button>
        </div>

        {/* Template Selector Dropdown */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowTemplateMenu((prev) => !prev)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700/80 rounded-lg border border-slate-200 dark:border-slate-700/60 transition-colors"
            title={t.templates}
          >
            <BookOpen className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400" />
            <span className="hidden md:inline">{t.templates}</span>
            <ChevronDown className="w-3 h-3 text-slate-500 dark:text-slate-400" />
          </button>

          {showTemplateMenu && (
            <div className="absolute right-0 top-full mt-1 w-44 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-lg shadow-xl py-1 text-xs text-slate-700 dark:text-slate-200 z-50 animate-in fade-in">
              <button
                type="button"
                onClick={() => {
                  onLoadTemplate('vi');
                  setShowTemplateMenu(false);
                }}
                className="w-full text-left px-3 py-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2"
              >
                <span>🇻🇳</span>
                <span>{t.templateVi}</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  onLoadTemplate('en');
                  setShowTemplateMenu(false);
                }}
                className="w-full text-left px-3 py-1.5 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2"
              >
                <span>🇬🇧</span>
                <span>{t.templateEn}</span>
              </button>
            </div>
          )}
        </div>

        {/* Layout View Toggles */}
        <div className="flex items-center bg-slate-100 dark:bg-slate-950/80 p-0.5 rounded-lg border border-slate-200 dark:border-slate-800 text-xs">
          <button
            type="button"
            onClick={() => onViewModeChange('split')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all ${
              viewMode === 'split'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
            title="Split-Screen View (Alt+Z)"
          >
            <Columns className="w-3.5 h-3.5" />
            <span className="hidden lg:inline">{t.splitView}</span>
          </button>
          <button
            type="button"
            onClick={() => onViewModeChange('editor')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all ${
              viewMode === 'editor'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
            title="Editor View Only"
          >
            <Code2 className="w-3.5 h-3.5" />
            <span className="hidden lg:inline">{t.sourceView}</span>
          </button>
          <button
            type="button"
            onClick={() => onViewModeChange('preview')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-md transition-all ${
              viewMode === 'preview'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
            }`}
            title="Rendered Preview Only"
          >
            <Eye className="w-3.5 h-3.5" />
            <span className="hidden lg:inline">{t.previewView}</span>
          </button>
        </div>

        {/* Reset / New Document */}
        <button
          type="button"
          onClick={onResetDocument}
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700/80 rounded-lg border border-slate-200 dark:border-slate-700/50 transition-colors"
          title={t.newDocumentTitle}
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{t.newDocument}</span>
        </button>
      </div>
    </header>
  );
};

export default Header;
