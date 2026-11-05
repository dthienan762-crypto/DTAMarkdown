import React, { useEffect, useState, forwardRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import hljs from 'highlight.js';
import { renderMermaidSvg } from '../lib/mermaidRenderer';
import { Copy, Check, AlertCircle } from 'lucide-react';

import { Locale, translations } from '../lib/i18n';

interface MarkdownPreviewProps {
  markdown: string;
  locale?: Locale;
  onScroll?: (e: React.UIEvent<HTMLDivElement>) => void;
  className?: string;
}

// Mermaid diagram execution component
const MermaidBlock: React.FC<{ code: string }> = ({ code }) => {
  const [svgContent, setSvgContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCancelled = false;

    renderMermaidSvg(code)
      .then((svg) => {
        if (!isCancelled) {
          setSvgContent(svg);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (!isCancelled) {
          setSvgContent(null);
          setError(err.message);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [code]);

  if (error) {
    return (
      <div className="my-4 p-3 bg-rose-950/30 border border-rose-800/50 rounded-lg text-xs font-mono text-rose-300">
        <div className="flex items-center gap-1.5 font-semibold text-rose-400 mb-1">
          <AlertCircle className="w-3.5 h-3.5" />
          Mermaid Render Error
        </div>
        <div className="text-[11px] text-rose-300/80 mb-2">{error}</div>
        <pre className="p-2 bg-slate-950/80 rounded text-[11px] overflow-x-auto text-slate-300">
          {code}
        </pre>
      </div>
    );
  }

  if (!svgContent) {
    return (
      <div className="my-4 p-6 bg-slate-900 border border-slate-800 rounded-lg flex items-center justify-center text-xs text-slate-500">
        Rendering diagram...
      </div>
    );
  }

  return (
    <div
      className="my-4 p-4 bg-slate-900/60 border border-slate-800 rounded-xl overflow-x-auto flex justify-center shadow-inner"
      dangerouslySetInnerHTML={{ __html: svgContent }}
    />
  );
};

// Syntax-highlighted code block with copy button
const CodeBlock: React.FC<{ language: string; code: string }> = ({ language, code }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  let highlightedHtml = '';
  try {
    if (language && hljs.getLanguage(language)) {
      highlightedHtml = hljs.highlight(code, {
        language,
        ignoreIllegals: true,
      }).value;
    } else {
      highlightedHtml = hljs.highlightAuto(code).value;
    }
  } catch {
    highlightedHtml = code;
  }

  return (
    <div className="relative group my-4 rounded-xl overflow-hidden border border-slate-800 bg-slate-900/90 shadow-md">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-slate-950/70 border-b border-slate-800 text-[11px] font-mono text-slate-400">
        <span>{language || 'code'}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 text-slate-400 hover:text-slate-200 transition-colors p-1 rounded"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400 text-[10px]">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span className="text-[10px]">Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="p-4 text-xs font-mono overflow-x-auto leading-relaxed">
        <code dangerouslySetInnerHTML={{ __html: highlightedHtml }} />
      </pre>
    </div>
  );
};

export const MarkdownPreview = forwardRef<HTMLDivElement, MarkdownPreviewProps>(
  ({ markdown, locale = 'vi', onScroll, className = '' }, ref) => {
    const t = translations[locale];

    return (
      <div
        ref={ref}
        onScroll={onScroll}
        className={`h-full overflow-y-auto px-6 py-6 text-slate-200 bg-slate-950 select-text ${className}`}
      >
        {markdown.trim().length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 text-sm italic select-none">
            <p>{t.previewEmpty}</p>
            <p className="text-xs text-slate-600 mt-1">
              {t.previewSupportNote}
            </p>
          </div>
        ) : (
          <article className="prose prose-invert prose-indigo max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkMath]}
              rehypePlugins={[[rehypeKatex, { throwOnError: false, errorColor: '#f43f5e' }]]}
              components={{
                code(props) {
                  const { children, className: codeClassName } = props;
                  const match = /language-(\w+)/.exec(codeClassName || '');
                  const lang = match ? match[1] : '';
                  const codeString = String(children).replace(/\n$/, '');

                  if (lang === 'mermaid') {
                    return <MermaidBlock code={codeString} />;
                  }

                  if (match) {
                    return <CodeBlock language={lang} code={codeString} />;
                  }

                  return (
                    <code className="px-1.5 py-0.5 rounded bg-slate-800/80 text-indigo-300 font-mono text-xs border border-slate-700/50">
                      {children}
                    </code>
                  );
                },
                table(props) {
                  return (
                    <div className="overflow-x-auto my-5 rounded-xl border border-slate-800 shadow-md">
                      <table className="min-w-full divide-y divide-slate-800 text-left text-sm" {...props} />
                    </div>
                  );
                },
                thead(props) {
                  return <thead className="bg-slate-900/90 text-slate-200" {...props} />;
                },
                tbody(props) {
                  return <tbody className="divide-y divide-slate-800/50 bg-slate-950/50" {...props} />;
                },
                th(props) {
                  return (
                    <th className="px-4 py-3 font-semibold text-xs uppercase tracking-wider text-slate-300" {...props} />
                  );
                },
                td(props) {
                  return (
                    <td className="px-4 py-2.5 text-xs text-slate-300" {...props} />
                  );
                },
                h1(props) {
                  return (
                    <h1
                      className="text-2xl font-bold text-slate-100 pb-2 mb-4 mt-2 border-b border-slate-800 tracking-tight"
                      {...props}
                    />
                  );
                },
                h2(props) {
                  return (
                    <h2
                      className="text-xl font-semibold text-slate-100 pb-1.5 mb-3 mt-6 border-b border-slate-800/60 tracking-tight"
                      {...props}
                    />
                  );
                },
                h3(props) {
                  return (
                    <h3 className="text-base font-semibold text-slate-200 mb-2 mt-5 tracking-tight" {...props} />
                  );
                },
                h4(props) {
                  return (
                    <h4 className="text-sm font-semibold text-slate-300 mb-1.5 mt-4" {...props} />
                  );
                },
                p(props) {
                  return <p className="leading-relaxed mb-4 text-slate-300 text-sm" {...props} />;
                },
                ul(props) {
                  return <ul className="list-disc list-outside pl-5 space-y-1 mb-4 text-sm text-slate-300" {...props} />;
                },
                ol(props) {
                  return <ol className="list-decimal list-outside pl-5 space-y-1 mb-4 text-sm text-slate-300" {...props} />;
                },
                li(props) {
                  return <li className="leading-relaxed" {...props} />;
                },
                blockquote(props) {
                  return (
                    <blockquote
                      className="border-l-4 border-indigo-500 pl-4 py-1 italic text-slate-400 my-4 bg-slate-900/40 rounded-r-lg"
                      {...props}
                    />
                  );
                },
                hr() {
                  return <hr className="my-6 border-slate-800" />;
                },
                a(props) {
                  return (
                    <a
                      className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 transition-colors"
                      target="_blank"
                      rel="noopener noreferrer"
                      {...props}
                    />
                  );
                },
              }}
            >
              {markdown}
            </ReactMarkdown>
          </article>
        )}
      </div>
    );
  }
);

MarkdownPreview.displayName = 'MarkdownPreview';
