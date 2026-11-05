import React, { useRef, useEffect, useCallback, useMemo } from 'react';
import CodeMirror, { ReactCodeMirrorRef } from '@uiw/react-codemirror';
import { markdown } from '@codemirror/lang-markdown';
import { oneDark } from '@codemirror/theme-one-dark';
import { EditorView } from '@codemirror/view';
import { MarkdownPreview } from './MarkdownPreview';
import { ViewMode } from './Header';
import { Locale, translations } from '../lib/i18n';
import {
  Bold,
  Italic,
  Heading1,
  Heading2,
  Table as TableIcon,
  Sigma,
  Code,
  List,
  GitBranch,
} from 'lucide-react';

interface LiveEditorProps {
  content: string;
  onChange: (value: string) => void;
  viewMode: ViewMode;
  locale?: Locale;
  isStreaming?: boolean;
}

export const LiveEditor: React.FC<LiveEditorProps> = ({
  content,
  onChange,
  viewMode,
  locale = 'vi',
  isStreaming = false,
}) => {
  const cmRef = useRef<ReactCodeMirrorRef | null>(null);
  const previewRef = useRef<HTMLDivElement | null>(null);
  const t = translations[locale];

  // Synchronized Ratio Scrolling Loop Suppression Flags
  const isSyncingLeftRef = useRef<boolean>(false);
  const isSyncingRightRef = useRef<boolean>(false);

  // Scroll sync from CodeMirror (Left) to Preview (Right)
  const handleEditorScroll = useCallback(() => {
    if (isSyncingLeftRef.current) {
      isSyncingLeftRef.current = false;
      return;
    }

    const editorView = cmRef.current?.view;
    const previewEl = previewRef.current;
    if (!editorView || !previewEl) return;

    const scrollDOM = editorView.scrollDOM;
    const maxEditorScroll = scrollDOM.scrollHeight - scrollDOM.clientHeight;
    if (maxEditorScroll <= 0) return;

    const ratio = scrollDOM.scrollTop / maxEditorScroll;
    const maxPreviewScroll = previewEl.scrollHeight - previewEl.clientHeight;

    isSyncingRightRef.current = true;
    previewEl.scrollTop = ratio * maxPreviewScroll;
  }, []);

  // Scroll sync from Preview (Right) to CodeMirror (Left)
  const handlePreviewScroll = useCallback(() => {
    if (isSyncingRightRef.current) {
      isSyncingRightRef.current = false;
      return;
    }

    const editorView = cmRef.current?.view;
    const previewEl = previewRef.current;
    if (!editorView || !previewEl) return;

    const scrollDOM = editorView.scrollDOM;
    const maxPreviewScroll = previewEl.scrollHeight - previewEl.clientHeight;
    if (maxPreviewScroll <= 0) return;

    const ratio = previewEl.scrollTop / maxPreviewScroll;
    const maxEditorScroll = scrollDOM.scrollHeight - scrollDOM.clientHeight;

    isSyncingLeftRef.current = true;
    scrollDOM.scrollTop = ratio * maxEditorScroll;
  }, []);

  // Attach listener to CodeMirror scrollDOM
  useEffect(() => {
    const editorView = cmRef.current?.view;
    if (!editorView) return;

    const scrollDOM = editorView.scrollDOM;
    scrollDOM.addEventListener('scroll', handleEditorScroll, { passive: true });

    return () => {
      scrollDOM.removeEventListener('scroll', handleEditorScroll);
    };
  }, [handleEditorScroll]);

  // Insert helper for formatting toolbar
  const insertFormatting = (prefix: string, suffix: string = '', defaultText: string = '') => {
    const view = cmRef.current?.view;
    if (!view) return;

    const state = view.state;
    const selection = state.selection.main;
    const selectedText = state.sliceDoc(selection.from, selection.to) || defaultText;

    const replacement = `${prefix}${selectedText}${suffix}`;
    view.dispatch({
      changes: {
        from: selection.from,
        to: selection.to,
        insert: replacement,
      },
      selection: {
        anchor: selection.from + prefix.length,
        head: selection.from + prefix.length + selectedText.length,
      },
    });
    view.focus();
  };

  // Custom CodeMirror theme customizations
  const editorTheme = useMemo(
    () =>
      EditorView.theme({
        '&': {
          height: '100%',
          backgroundColor: '#020617',
          fontSize: '13px',
          fontFamily: '"JetBrains Mono", Consolas, Menlo, monospace',
        },
        '.cm-scroller': {
          fontFamily: 'inherit',
          lineHeight: '1.65',
        },
        '.cm-gutters': {
          backgroundColor: '#090d16',
          color: '#475569',
          borderRight: '1px solid #1e293b',
        },
        '.cm-activeLine': {
          backgroundColor: '#0f172a80',
        },
        '.cm-activeLineGutter': {
          backgroundColor: '#1e293b60',
          color: '#cbd5e1',
        },
      }),
    []
  );

  return (
    <div className="flex-1 flex flex-col min-h-0 bg-white dark:bg-slate-950 transition-colors duration-200">
      {/* Editor Toolbar */}
      {viewMode !== 'preview' && (
        <div className="h-10 bg-slate-100/90 dark:bg-slate-900/80 border-b border-slate-200 dark:border-slate-800 px-3 sm:px-4 flex items-center gap-1 shrink-0 overflow-x-auto text-slate-600 dark:text-slate-400 select-none">
          <button
            type="button"
            onClick={() => insertFormatting('**', '**', locale === 'vi' ? 'chữ đậm' : 'bold text')}
            className="p-1.5 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 rounded transition-colors"
            title={t.bold}
          >
            <Bold className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => insertFormatting('*', '*', locale === 'vi' ? 'chữ nghiêng' : 'italic text')}
            className="p-1.5 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors"
            title={t.italic}
          >
            <Italic className="w-3.5 h-3.5" />
          </button>
          <div className="h-4 w-[1px] bg-slate-300 dark:bg-slate-800 mx-1" />
          <button
            type="button"
            onClick={() => insertFormatting('# ', '', locale === 'vi' ? 'Tiêu Đề 1' : 'Heading 1')}
            className="p-1.5 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 rounded transition-colors"
            title={t.heading1}
          >
            <Heading1 className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => insertFormatting('## ', '', locale === 'vi' ? 'Tiêu Đề 2' : 'Heading 2')}
            className="p-1.5 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 rounded transition-colors"
            title={t.heading2}
          >
            <Heading2 className="w-3.5 h-3.5" />
          </button>
          <div className="h-4 w-[1px] bg-slate-300 dark:bg-slate-800 mx-1" />
          <button
            type="button"
            onClick={() =>
              insertFormatting(
                locale === 'vi'
                  ? '\n| Cột 1 | Cột 2 | Cột 3 |\n|---|---|---|\n| Dữ liệu A | Dữ liệu B | Dữ liệu C |\n'
                  : '\n| Column 1 | Column 2 | Column 3 |\n|---|---|---|\n| Data A | Data B | Data C |\n'
              )
            }
            className="p-1.5 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 rounded transition-colors"
            title={t.insertTable}
          >
            <TableIcon className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() => insertFormatting('$$\n', '\n$$', 'f(x) = \\sum_{i=1}^n x_i')}
            className="p-1.5 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 rounded transition-colors"
            title={t.insertMath}
          >
            <Sigma className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400" />
          </button>
          <button
            type="button"
            onClick={() => insertFormatting('```typescript\n', '\n```', '// code')}
            className="p-1.5 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 rounded transition-colors"
            title={t.insertCode}
          >
            <Code className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={() =>
              insertFormatting(
                locale === 'vi'
                  ? '```mermaid\ngraph TD\n  A[Bắt đầu] --> B{Xử lý}\n  B -->|Đạt| C[Xuất bản Markdown]\n  B -->|Lỗi| D[Thử lại]\n```\n'
                  : '```mermaid\ngraph TD\n  A[Start] --> B{Evaluate}\n  B -->|Pass| C[Markdown Studio]\n  B -->|Fail| D[Retry]\n```\n'
              )
            }
            className="p-1.5 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 rounded transition-colors"
            title={t.insertMermaid}
          >
            <GitBranch className="w-3.5 h-3.5 text-purple-500 dark:text-purple-400" />
          </button>
          <button
            type="button"
            onClick={() => insertFormatting('- ', '', locale === 'vi' ? 'Mục danh sách' : 'List item')}
            className="p-1.5 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 rounded transition-colors"
            title={t.insertList}
          >
            <List className="w-3.5 h-3.5" />
          </button>

          {isStreaming && (
            <div className="ml-auto flex items-center gap-1.5 text-xs text-indigo-500 dark:text-indigo-400 animate-pulse">
              <span className="w-2 h-2 rounded-full bg-indigo-500" />
              <span>{t.streamingInput}</span>
            </div>
          )}
        </div>
      )}

      {/* Main Split Body */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* Editor Pane (Left) */}
        {viewMode !== 'preview' && (
          <div
            className={`h-full flex flex-col min-h-0 border-r border-slate-200 dark:border-slate-800 ${
              viewMode === 'split' ? 'w-1/2' : 'w-full'
            }`}
          >
            <div className="flex-1 min-h-0 overflow-hidden relative">
              <CodeMirror
                ref={cmRef}
                value={content}
                height="100%"
                theme={oneDark}
                extensions={[markdown(), editorTheme]}
                onChange={onChange}
                className="h-full"
                basicSetup={{
                  lineNumbers: true,
                  highlightActiveLineGutter: true,
                  highlightActiveLine: true,
                  foldGutter: true,
                  dropCursor: true,
                  allowMultipleSelections: true,
                  indentOnInput: true,
                  bracketMatching: true,
                  closeBrackets: true,
                  autocompletion: true,
                  rectangularSelection: true,
                  crosshairCursor: true,
                }}
              />
            </div>
          </div>
        )}

        {/* Live Preview Pane (Right) */}
        {viewMode !== 'editor' && (
          <div
            className={`h-full min-h-0 ${
              viewMode === 'split' ? 'w-1/2' : 'w-full'
            }`}
          >
            <MarkdownPreview
              ref={previewRef}
              markdown={content}
              locale={locale}
              onScroll={handlePreviewScroll}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default LiveEditor;
