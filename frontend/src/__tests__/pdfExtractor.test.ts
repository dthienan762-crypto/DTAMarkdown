import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import { extractPdfTextFromBuffer } from '../lib/pdfExtractor';

describe('PDF Native Extractor', () => {
  it('extracts digital vector text, tables, and KaTeX math from digital_sample.pdf', async () => {
    const samplePath = path.resolve(__dirname, '../../../tests/data/vision/digital_sample.pdf');
    if (!fs.existsSync(samplePath)) {
      console.warn('Skipping test, sample file not found at:', samplePath);
      return;
    }

    const buffer = fs.readFileSync(samplePath);
    const text = await extractPdfTextFromBuffer(new Uint8Array(buffer));

    expect(text).toContain('Digital Vector Document');
    expect(text).toContain('Executive Summary');
    expect(text).toContain('System Architecture');
    expect(text).toContain('| Component | Implementation | Latency Target | Status |');
    expect(text).toContain('f(x) = \\frac{1}{\\sigma \\sqrt{2\\pi}}');
  });
});
