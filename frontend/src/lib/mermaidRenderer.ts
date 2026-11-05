import mermaid from 'mermaid';

let initialized = false;

export function initializeMermaid(): void {
  if (initialized) return;

  mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    securityLevel: 'loose',
    fontFamily: 'Inter, system-ui, sans-serif',
    themeVariables: {
      darkMode: true,
      background: '#0f172a',
      primaryColor: '#4f46e5',
      primaryTextColor: '#f1f5f9',
      primaryBorderColor: '#6366f1',
      lineColor: '#94a3b8',
      secondaryColor: '#1e293b',
      tertiaryColor: '#020617',
      edgeLabelBackground: '#1e293b',
    },
  });

  initialized = true;
}

let counter = 0;

export async function renderMermaidSvg(code: string): Promise<string> {
  initializeMermaid();
  counter += 1;
  const id = `mermaid-svg-${Date.now()}-${counter}`;

  try {
    // mermaid.render will inject an svg into container or return svg string
    const result = await mermaid.render(id, code);
    return result.svg;
  } catch (err: unknown) {
    // Clean up temporary DOM element that mermaid may have left behind
    const orphan = document.getElementById(id);
    if (orphan) {
      orphan.remove();
    }
    const message = err instanceof Error ? err.message : 'Invalid Mermaid syntax';
    throw new Error(message);
  }
}
