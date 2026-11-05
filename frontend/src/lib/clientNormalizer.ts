/**
 * DTAMarkdown Studio - Client-Side Resilient Conversion Engine.
 * Provides instant, zero-dependency offline normalization for text, HTML, and tables.
 * Used as primary engine on static web hosts (Vercel) and instant fallback when backend is unreachable.
 * Tác giả: Đinh Thiên Ân <dthienan762@gmail.com>
 */

import { ConversionOptions, ConversionResult, ConversionMetadata } from '../types';

/**
 * Escapes pipe characters inside table cells.
 */
function escapePipes(text: string): string {
  return text.replace(/(?<!\\)\|/g, '\\|').trim();
}

/**
 * Converts an HTML Table Element into clean GitHub Flavored Markdown (GFM).
 */
function convertHtmlTableToGfm(tableEl: HTMLTableElement): string {
  const rows = Array.from(tableEl.querySelectorAll('tr'));
  if (rows.length === 0) return '';

  const tableData: string[][] = [];

  rows.forEach((tr) => {
    const cells = Array.from(tr.querySelectorAll('th, td'));
    const rowValues: string[] = [];

    cells.forEach((cell) => {
      // Resolve line breaks inside cells to <br>
      let cellText = cell.innerHTML
        .replace(/<br\s*\/?>/gi, '<br>')
        .replace(/\n+/g, ' ')
        .trim();

      // Convert inner bold/italic/links if present
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = cellText;
      const plainText = tempDiv.textContent || tempDiv.innerText || '';
      rowValues.push(escapePipes(plainText));
    });

    if (rowValues.length > 0) {
      tableData.push(rowValues);
    }
  });

  if (tableData.length === 0) return '';

  // Calculate max columns across rows to guarantee symmetry
  const maxCols = Math.max(...tableData.map((r) => r.length));
  if (maxCols === 0) return '';

  // Pad short rows
  const normalizedRows = tableData.map((row) => {
    while (row.length < maxCols) {
      row.push('');
    }
    return row;
  });

  const headerRow = normalizedRows[0];
  const separatorRow = new Array(maxCols).fill('---');
  const bodyRows = normalizedRows.slice(1);

  const lines: string[] = [
    `| ${headerRow.join(' | ')} |`,
    `| ${separatorRow.join(' | ')} |`,
  ];

  bodyRows.forEach((row) => {
    lines.push(`| ${row.join(' | ')} |`);
  });

  return `\n\n${lines.join('\n')}\n\n`;
}

/**
 * Converts arbitrary HTML content into standard Markdown.
 */
function htmlToMarkdown(html: string): string {
  if (typeof window === 'undefined' || !html.includes('<')) {
    return html;
  }

  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');

  // 1. Process HTML tables first
  const tables = Array.from(doc.querySelectorAll('table'));
  tables.forEach((table) => {
    const gfmTable = convertHtmlTableToGfm(table as HTMLTableElement);
    const textNode = doc.createTextNode(gfmTable);
    table.parentNode?.replaceChild(textNode, table);
  });

  // 2. Process Headings
  for (let i = 1; i <= 6; i++) {
    const headers = Array.from(doc.querySelectorAll(`h${i}`));
    headers.forEach((h) => {
      const hashes = '#'.repeat(i);
      const text = (h.textContent || '').trim();
      const node = doc.createTextNode(`\n\n${hashes} ${text}\n\n`);
      h.parentNode?.replaceChild(node, h);
    });
  }

  // 3. Process Code Blocks
  const pres = Array.from(doc.querySelectorAll('pre'));
  pres.forEach((pre) => {
    const code = pre.querySelector('code')?.textContent || pre.textContent || '';
    const node = doc.createTextNode(`\n\n\`\`\`\n${code.trim()}\n\`\`\`\n\n`);
    pre.parentNode?.replaceChild(node, pre);
  });

  // 4. Process Inline Code
  const codes = Array.from(doc.querySelectorAll('code'));
  codes.forEach((c) => {
    const text = c.textContent || '';
    const node = doc.createTextNode(`\`${text}\``);
    c.parentNode?.replaceChild(node, c);
  });

  // 5. Process Blockquotes
  const quotes = Array.from(doc.querySelectorAll('blockquote'));
  quotes.forEach((q) => {
    const text = (q.textContent || '').trim();
    const node = doc.createTextNode(`\n\n> ${text}\n\n`);
    q.parentNode?.replaceChild(node, q);
  });

  // 6. Process Lists
  const uls = Array.from(doc.querySelectorAll('ul'));
  uls.forEach((ul) => {
    const lis = Array.from(ul.querySelectorAll('li'));
    const items = lis.map((li) => `- ${(li.textContent || '').trim()}`).join('\n');
    const node = doc.createTextNode(`\n\n${items}\n\n`);
    ul.parentNode?.replaceChild(node, ul);
  });

  const ols = Array.from(doc.querySelectorAll('ol'));
  ols.forEach((ol) => {
    const lis = Array.from(ol.querySelectorAll('li'));
    const items = lis.map((li, idx) => `${idx + 1}. ${(li.textContent || '').trim()}`).join('\n');
    const node = doc.createTextNode(`\n\n${items}\n\n`);
    ol.parentNode?.replaceChild(node, ol);
  });

  // 7. Process Paragraphs & Line Breaks
  const ps = Array.from(doc.querySelectorAll('p'));
  ps.forEach((p) => {
    const text = (p.textContent || '').trim();
    const node = doc.createTextNode(`\n\n${text}\n\n`);
    p.parentNode?.replaceChild(node, p);
  });

  const brs = Array.from(doc.querySelectorAll('br'));
  brs.forEach((br) => {
    const node = doc.createTextNode('\n');
    br.parentNode?.replaceChild(node, br);
  });

  // 8. Process Bold and Italic
  const strongs = Array.from(doc.querySelectorAll('strong, b'));
  strongs.forEach((b) => {
    const text = (b.textContent || '').trim();
    const node = doc.createTextNode(` **${text}** `);
    b.parentNode?.replaceChild(node, b);
  });

  const ems = Array.from(doc.querySelectorAll('em, i'));
  ems.forEach((em) => {
    const text = (em.textContent || '').trim();
    const node = doc.createTextNode(` *${text}* `);
    em.parentNode?.replaceChild(node, em);
  });

  return doc.body.textContent || doc.body.innerText || html;
}

/**
 * Creates GitHub-style URL anchor slugs from heading text (including Vietnamese Unicode).
 */
function slugifyHeading(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s-]/gu, '')
    .trim()
    .replace(/\s+/g, '-');
}

/**
 * Generates an automatic Table of Contents from Markdown headings.
 */
function generateClientToc(markdown: string): string | null {
  const headingRegex = /^(#{1,6})\s+(.+)$/gm;
  const tocEntries: string[] = [];
  let match;

  while ((match = headingRegex.exec(markdown)) !== null) {
    const level = match[1].length;
    const title = match[2].trim();
    // Exclude existing TOC header
    if (/^(mục lục|table of contents|contents|toc)$/i.test(title)) {
      continue;
    }
    const indent = '  '.repeat(Math.max(0, level - 1));
    const slug = slugifyHeading(title);
    tocEntries.push(`${indent}- [${title}](#${slug})`);
  }

  if (tocEntries.length < 2) return null;

  return `## Mục Lục\n\n${tocEntries.join('\n')}\n\n---`;
}

/**
 * Normalizes raw text or HTML in the browser with full fidelity.
 */
export function clientNormalizeText(
  rawText: string,
  options?: ConversionOptions
): ConversionResult {
  const startTime = performance.now();

  if (!rawText || !rawText.trim()) {
    return {
      job_id: `client-${Date.now()}`,
      success: true,
      pipeline: 'text_normalize',
      markdown: '',
      metadata: {
        word_count: 0,
        character_count: 0,
        estimated_read_time: '1 min',
        duration_ms: 1,
        engine_used: 'DTAMarkdown Client Engine (Offline / Vercel)',
        tags: ['markdown', 'client_engine'],
      },
      warnings: [],
      duration_ms: 1,
    };
  }

  let text = rawText;

  // 1. MathShield: Shield inline and display KaTeX formulas
  const mathBlocks: string[] = [];
  const mathInlines: string[] = [];

  // Shield display math $$...$$
  text = text.replace(/\$\$([\s\S]*?)\$\$/g, (_, eq) => {
    const placeholder = `__MATH_SHIELD_BLOCK_${mathBlocks.length}__`;
    mathBlocks.push(eq);
    return placeholder;
  });

  // Shield inline math $...$
  text = text.replace(/\$([^\$\n]+?)\$/g, (_, eq) => {
    const placeholder = `__MATH_SHIELD_INLINE_${mathInlines.length}__`;
    mathInlines.push(eq);
    return placeholder;
  });

  // 2. Convert HTML formatting & tables
  if (/<[a-z][\s\S]*>/i.test(text)) {
    text = htmlToMarkdown(text);
  }

  // 3. Unshield Math
  mathBlocks.forEach((eq, idx) => {
    text = text.replace(`__MATH_SHIELD_BLOCK_${idx}__`, `$$\n${eq.trim()}\n$$`);
  });

  mathInlines.forEach((eq, idx) => {
    text = text.replace(`__MATH_SHIELD_INLINE_${idx}__`, `$${eq.trim()}$`);
  });

  // 4. Normalize multiple whitespace and clean lines
  text = text.replace(/\r\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();

  // 5. Generate TOC if requested
  let toc: string | null = null;
  if (options?.generate_toc !== false) {
    toc = generateClientToc(text);
    if (toc && !/^(#+\s+(mục lục|table of contents))/im.test(text)) {
      // Inject TOC right after the first H1 heading, or at the top
      const firstH1Match = text.match(/^#\s+.+$/m);
      if (firstH1Match && firstH1Match.index !== undefined) {
        const insertPos = firstH1Match.index + firstH1Match[0].length;
        text = `${text.slice(0, insertPos)}\n\n${toc}\n\n${text.slice(insertPos).trim()}`;
      } else {
        text = `${toc}\n\n${text}`;
      }
    }
  }

  const durationMs = Math.round(performance.now() - startTime);
  const words = text.trim().split(/\s+/).filter(Boolean);
  const wordCount = words.length;
  const characterCount = text.length;
  const readTimeMin = Math.max(1, Math.ceil(wordCount / 200));

  const metadata: ConversionMetadata = {
    word_count: wordCount,
    character_count: characterCount,
    estimated_read_time: `${readTimeMin} min`,
    duration_ms: durationMs,
    engine_used: 'DTAMarkdown Client Engine (Offline / Vercel)',
    tags: ['markdown', 'text_normalize', 'vietnamese_optimized'],
    toc: toc || undefined,
  };

  return {
    job_id: `client-${Date.now()}`,
    success: true,
    pipeline: 'text_normalize',
    markdown: text,
    metadata,
    warnings: [],
    duration_ms: durationMs,
  };
}
