# DTAMarkdown Studio

> Production-grade full-stack multimodal Markdown conversion workbench. Transform scanned documents, degraded images, voice recordings, messy HTML, and raw unstructured text into pristine GitHub Flavored Markdown (GFM) with preserved tables, KaTeX math formulas, Mermaid diagrams, and automatic Tables of Contents.

---

## 🌟 Key Capabilities

1. **Vision OCR Pipeline (`/ai-pipelines/vision_ocr/`)**:
   - High-fidelity table extraction into strict GitHub Flavored Markdown (GFM) tables without column misalignment.
   - Mathematical formula extraction into valid KaTeX/LaTeX `$inline$` and `$$display$$` syntax.
   - Multi-tier engine architecture: PyMuPDF fast-path for digital PDFs, Multimodal Vision API primary, and RapidOCR (pure ONNX Runtime) offline fallback.
   - Zero external CLI binary dependency (runs without system `tesseract.exe`).

2. **Voice STT Pipeline (`/ai-pipelines/voice_stt/`)**:
   - Ingestion of 16-bit PCM WAV (16kHz mono) recorded directly via browser Web Audio API or uploaded files.
   - Automatic punctuation, capitalization, and silence-gap paragraph segmentation.
   - Markdown timestamp annotations formatted as `**[HH:MM:SS]**`.
   - Zero external CLI binary dependency (runs without system `ffmpeg.exe`).

3. **Text Normalization Engine (`/ai-pipelines/text_engine/`)**:
   - Conversion of messy HTML, unclosed tags, and raw text into clean Markdown.
   - Table flattening, colspan/rowspan resolution, and pipe (`\|`) escaping.
   - MathShield protection for `$..$` and `$$..$$` formulas during HTML transformations.
   - Automatic hierarchical Table of Contents (TOC) generator with GitHub slug anchors.
   - Automated keyword tag extraction and YAML frontmatter injection.

4. **FastAPI Real-Time Streaming Server (`/backend/`)**:
   - Strict adherence to the OpenAPI 3.1.0 contract at `/docs/specs/api_contract.yaml`.
   - Full-duplex WebSocket streaming (`/api/v1/ws/stream/{job_id}`) yielding real-time conversion chunks and progress events.
   - In-memory `JobManager` with bounded concurrency semaphore (`asyncio.Semaphore(4)`).
   - Secure temp file lifecycle: UUID-isolated staging, context-managed unlinking, and 10-minute periodic reaper sweeps.

5. **Live Markdown Studio Frontend (`/frontend/`)**:
   - Modern responsive UI built with React 19, TypeScript, Vite, and TailwindCSS (Slate/Zinc/Indigo palette).
   - Instant clipboard paste (`Ctrl+V`) for images and HTML tables.
   - Multi-file drag-and-drop dropzone with status queue cards.
   - Microphone voice recording with real-time HTML5 Canvas waveform visualizer powered by Web Audio API (`AnalyserNode`).
   - Side-by-side split-screen CodeMirror 6 editor with synchronized scrolling.
   - Live rendering supporting KaTeX equations, Mermaid.js diagrams, and syntax highlighting.
   - One-click export to `.md`, standalone styled HTML, and print/PDF.

---

## 🏗️ Architecture & Monorepo Structure

```
d:\markdown tự code\
├── docs\
│   └── specs\                     # Shared Architecture & Specifications
│       ├── core_principles.md     # 6 Core Architectural Principles
│       ├── product_ux.md          # Comprehensive UX Specification & Design System
│       └── api_contract.yaml      # OpenAPI 3.1.0 & WebSocket Protocol Definition
├── ai-pipelines\                  # Multimodal Conversion Engines
│   ├── vision_ocr\                # Table & KaTeX OCR (PyMuPDF, Gemini, RapidOCR)
│   ├── voice_stt\                 # Audio Transcription & Markdown Timestamps
│   ├── text_engine\               # HTML/Text Normalization, TOC & Tag Generation
│   ├── schemas.py                 # Pydantic v2 Pipeline Contracts
│   └── pipeline_runner.py         # Unified async engine dispatcher
├── backend\                       # Backend Server & Real-time Services
│   ├── app\
│   │   ├── main.py                # FastAPI Application Entrypoint
│   │   ├── config.py              # Application Configuration & Environment Settings
│   │   ├── routes\                # REST Endpoints (convert, jobs, export, health)
│   │   ├── services\              # JobManager & ManagedTempFile Lifecycle
│   │   └── websocket\             # WebSocket Connection & Streaming Manager
│   ├── requirements.txt           # Python backend dependencies
│   └── run.py                     # Server launch script (Uvicorn)
├── frontend\                      # Live Studio Web Application
│   ├── src\
│   │   ├── components\            # Header, IngestionZone, LiveEditor, Preview, etc.
│   │   ├── hooks\                 # useAudioRecorder, useClipboardPaste, useWebSocketStream
│   │   ├── lib\                   # API client, KaTeX plugins, Mermaid rendering
│   │   ├── App.tsx                # Studio layout shell
│   │   └── main.tsx               # Client entrypoint
│   ├── package.json               # Node.js dependencies
│   ├── vite.config.ts             # Vite build & proxy configuration
│   └── tailwind.config.js         # TailwindCSS styling configuration
└── tests\                         # Verification & Quality Assurance
    ├── data\                      # Synthetic multimodal fixtures (vision, audio, text)
    ├── unit\                      # Pipeline and backend unit tests
    ├── integration\               # API and WebSocket integration tests
    └── e2e\                       # Playwright browser end-to-end tests
```

---

## 🚀 Developer Quickstart

### Prerequisites
- **Python**: 3.10+ (tested on Python 3.14.3 64-bit)
- **Node.js**: v20+ (tested on Node.js v26.13.0 & npm 11.20.0)
- **Git**: 2.30+

### 1. Backend & AI Pipelines Setup
```powershell
# Navigate to backend directory
cd "d:\markdown tự code\backend"

# Install dependencies (or run in root Python environment)
pip install -r requirements.txt

# Start backend server
python run.py
# Server runs at http://localhost:8000
# OpenAPI documentation available at http://localhost:8000/docs
```

### 2. Frontend Live Studio Setup
```powershell
# Navigate to frontend directory
cd "d:\markdown tự code\frontend"

# Install npm packages
npm install

# Start Vite dev server with HMR
npm run dev
# Frontend runs at http://localhost:5173
```

### 3. Automated Test Execution
```powershell
# Run backend and pipeline unit/integration tests
pytest tests/unit tests/integration -v

# Run Playwright browser end-to-end tests
npx playwright test
```

---

## 📜 Specifications & Contracts

All components strictly follow pre-published specifications in `/docs/specs/`:
- **`core_principles.md`**: Core technical tenets including Contract-First, Non-Blocking Real-time Streaming, Zero Data Leakage & Tempfile Lifecycle, Zero-CLI Binary Dependency, KaTeX Math & Table Structural Integrity, and Graceful Degradation.
- **`product_ux.md`**: Visual design system, responsive layout wireframes, user interaction workflows (Clipboard paste, drag-and-drop, mic waveform, split editor), and keyboard shortcuts.
- **`api_contract.yaml`**: Full OpenAPI 3.1.0 schema defining REST conversion/export endpoints and bidirectional WebSocket streaming frames.
