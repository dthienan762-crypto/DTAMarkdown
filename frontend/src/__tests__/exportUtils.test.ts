import { describe, it, expect } from 'vitest';

function extractTitle(content: string): string {
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
  return 'document';
}

function sanitizeFileName(title: string): string {
  return (
    title
      .toLowerCase()
      .replace(/[^a-z0-9_-]/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '') || 'document'
  );
}

function computeStats(content: string) {
  const chars = content.length;
  const words = content.trim().length === 0 ? 0 : content.trim().split(/\s+/).length;
  const readingTimeMinutes = Math.max(1, Math.ceil(words / 200));
  return { chars, words, readingTime: `${readingTimeMinutes} min read` };
}

describe('exportUtils', () => {
  it('extracts title correctly from Markdown header', () => {
    const md = `# Quarterly Financial Report 2026\n\nSome text here.`;
    expect(extractTitle(md)).toBe('Quarterly Financial Report 2026');
  });

  it('falls back to first non-empty text if no H1 header exists', () => {
    const md = `\n\nMeeting notes from executive committee.\nNext line.`;
    expect(extractTitle(md)).toBe('Meeting notes from executive committee.');
  });

  it('sanitizes titles into valid filenames without special characters', () => {
    expect(sanitizeFileName('Quarterly Financial Report 2026!')).toBe(
      'quarterly-financial-report-2026'
    );
    expect(sanitizeFileName('  ---Special @#$ Name---  ')).toBe('special-name');
    expect(sanitizeFileName('')).toBe('document');
  });

  it('computes word count and reading time correctly', () => {
    const emptyStats = computeStats('');
    expect(emptyStats.words).toBe(0);
    expect(emptyStats.chars).toBe(0);

    const text = 'One two three four five six seven eight nine ten.';
    const stats = computeStats(text);
    expect(stats.words).toBe(10);
    expect(stats.readingTime).toBe('1 min read');
  });
});
