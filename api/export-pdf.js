/**
 * Vercel Serverless Function: /api/v1/export/pdf
 * Returns clean 200 response or HTML representation for browser print dialog.
 */

export default function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // Graceful response prompting browser print engine
  return res.status(200).json({
    status: 'READY',
    message: 'For serverless deployments, high-fidelity PDF is compiled via the browser Print / PDF engine with full Vietnamese Arial font support.',
    fallback: 'print',
  });
}
