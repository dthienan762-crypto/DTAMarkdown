/**
 * Vercel Serverless Function: Text & Table Normalization Endpoint
 * Route: /api/v1/convert/text -> /api/convert-text
 * Tác giả: Đinh Thiên Ân <dthienan762@gmail.com>
 */

export default function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ message: 'Method not allowed' });
  }

  const body = req.body || {};
  const rawText = body.raw_text || '';

  if (!rawText || !rawText.trim()) {
    return res.status(400).json({
      detail: {
        code: 'EMPTY_TEXT_PAYLOAD',
        message: 'Raw text input cannot be empty.',
      },
    });
  }

  const startTime = Date.now();
  let text = rawText.trim();

  // Basic HTML tag stripping/conversion if HTML detected
  if (/<[a-z][\s\S]*>/i.test(text)) {
    text = text
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/p>/gi, '\n\n')
      .replace(/<\/h[1-6]>/gi, '\n\n')
      .replace(/<h1[^>]*>/gi, '# ')
      .replace(/<h2[^>]*>/gi, '## ')
      .replace(/<h3[^>]*>/gi, '### ')
      .replace(/<strong[^>]*>|<\/strong>|<b[^>]*>|<\/b>/gi, '**')
      .replace(/<em[^>]*>|<\/em>|<i[^>]*>|<\/i>/gi, '*')
      .replace(/<code[^>]*>|<\/code>/gi, '`')
      .replace(/<[^>]+>/g, '')
      .replace(/&nbsp;/gi, ' ')
      .replace(/&amp;/gi, '&')
      .replace(/&lt;/gi, '<')
      .replace(/&gt;/gi, '>')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  }

  const words = text.split(/\s+/).filter(Boolean).length;
  const durationMs = Math.max(1, Date.now() - startTime);

  return res.status(200).json({
    job_id: `vercel-${Date.now()}`,
    success: true,
    pipeline: body.pipeline_type || 'text_normalize',
    markdown: text,
    metadata: {
      word_count: words,
      character_count: text.length,
      estimated_read_time: `${Math.max(1, Math.ceil(words / 200))} min`,
      duration_ms: durationMs,
      engine_used: 'Vercel Serverless Normalizer',
      tags: ['markdown', 'text_normalize', 'vercel_serverless'],
    },
    warnings: [],
    duration_ms: durationMs,
  });
}

