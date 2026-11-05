import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendTarget = env.VITE_BACKEND_URL || env.BACKEND_URL || 'http://localhost:8000';

  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: false,
      open: true, // Automatically open default browser when dev server starts
      proxy: {
        '/api': {
          target: backendTarget,
          changeOrigin: true,
          ws: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
      chunkSizeWarningLimit: 1200,
      rollupOptions: {
        output: {
          manualChunks: {
            'vendor-react': ['react', 'react-dom'],
            'vendor-codemirror': [
              '@uiw/react-codemirror',
              '@codemirror/lang-markdown',
              '@codemirror/language',
              '@codemirror/state',
              '@codemirror/view',
              '@codemirror/theme-one-dark',
            ],
            'vendor-markdown': [
              'react-markdown',
              'remark-gfm',
              'remark-math',
              'rehype-katex',
              'katex',
            ],
            'vendor-mermaid': ['mermaid'],
          },
        },
      },
    },
  };
});
