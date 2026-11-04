# Project: DTAMarkdown Studio

## Architecture
DTAMarkdown Studio is a production full-stack web application designed for multimodal conversion of unstructured content (Scanned Documents & Images, Voice & Audio recordings, Messy HTML & Unstructured Text) into standard, clean, well-formatted Markdown with KaTeX math formulas, Mermaid diagrams, and preserved table layouts.

The project follows a 3-phase handoff workflow across 6 specialized functional domains communicating contract-first via `/docs/specs/`:
```
                          [/docs/specs/]
               (Core Principles, Product UX, API Contract)
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
 [/ai-pipelines/]          [/backend/]             [/frontend/]
  - Vision OCR              - FastAPI Server        - React/Vite/TS
  - Voice STT               - Async Queue           - Live Split Editor
  - Text Normalizer         - WebSocket Stream      - Ingestion / Waveform
        │                       │                       │
        └───────────────────────┼───────────────────────┘
                                ▼
                           [/tests/]
                 - Synthetic Data Fixtures
                 - Unit & Integration Tests
                 - Browser E2E Test Suite
```

### Communication & Data Flow
1. **Contract-First**: All shared contracts are pre-published in `/docs/specs/` (`core_principles.md`, `product_ux.md`, `api_contract.yaml`).
2. **Real-Time Streaming**: Asynchronous workers in `/ai-pipelines/` stream progressive Markdown chunks to `/backend/` via async queues, forwarded over WebSocket (`/api/v1/ws/stream/{job_id}`) to `/frontend/`.
3. **Dual Track Execution**: Parallel Implementation Track builds the product components (M1 -> M2/M3/M4 concurrent -> M5), while the E2E Testing Track independently designs opaque-box tests and publishes `TEST_READY.md`.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Monorepo & Git Worktree Setup | Initialize Git, .gitignore, and monorepo structure (`/frontend`, `/backend`, `/ai-pipelines`, `/tests`, `/docs/specs/`) | M1 | R4, Env Survey |
| 2 | Technical Core Principles Spec | Author `/docs/specs/core_principles.md` defining tenets, error handling, tempfile lifecycle | M1 | R4, Web Survey |
| 3 | Product UX Specification | Author `/docs/specs/product_ux.md` defining layout, color palette, editor split, waveform UX | M1 | R4, Web Survey |
| 4 | OpenAPI 3.1 & WebSocket Contract | Author `/docs/specs/api_contract.yaml` specifying all REST endpoints and WebSocket protocols | M1 | R2, R4 |
| 5 | Vision OCR - Table Extraction | Parse scanned documents/images into valid Markdown tables without misalignment | M2 | R1, AI Survey |
| 6 | Vision OCR - Math Formula Extraction | Extract mathematical formulas into KaTeX/LaTeX `$..$` (inline) and `$$..$$` (display) | M2 | R1, AI Survey |
| 7 | Vision OCR - Multi-tier Engine Fallback | PyMuPDF fast-path for digital PDFs, Gemini Vision API primary, RapidOCR ONNX offline fallback | M2 | R1, AI Survey |
| 8 | Voice STT - Audio Transcription | Transcribe audio files and microphone input with automatic punctuation & capitalization | M2 | R1, AI Survey |
| 9 | Voice STT - Paragraph Segmentation & Timestamps | Silence-gap paragraphing with Markdown timestamp annotations `**[HH:MM:SS]**` | M2 | R1, AI Survey |
| 10 | Voice STT - Direct 16-bit PCM WAV Pipeline | Direct ingestion of 16-bit PCM WAV (16kHz), removing external ffmpeg binary dependency | M2 | R1, AI Survey |
| 11 | Text Engine - HTML & Table Normalization | Convert messy HTML, flatten nested tables, resolve colspan/rowspan, escape pipes `\|` | M2 | R1, AI Survey |
| 12 | Text Engine - LaTeX Delimiter Shielding | MathShield to protect `$..$` and `$$..$$` during HTML/text parsing | M2 | R1, AI Survey |
| 13 | Text Engine - Automatic TOC Generation | Generate hierarchical Table of Contents with GitHub slug anchors from document headings | M2 | R1, AI Survey |
| 14 | Text Engine - Tag & Metadata Extraction | Extract keyword tags, word count, reading time, and generate YAML frontmatter | M2 | R1, AI Survey |
| 15 | Backend FastAPI Server & REST Endpoints | Implement FastAPI application strictly conforming to `/docs/specs/api_contract.yaml` | M3 | R2, Web Survey |
| 16 | Backend WebSocket Real-time Streaming | Stream incremental Markdown chunks over `/api/v1/ws/stream/{job_id}` via asyncio.Queue | M3 | R2, Web Survey |
| 17 | Backend Async Queue & Job Manager | In-memory JobManager with bounded semaphore to manage concurrent heavy conversions | M3 | R2, Web Survey |
| 18 | Backend Secure Staging & Temp Reaper | UUID-based temp file staging, context manager unlinking, 10-min background cleanup task | M3 | R2, Web Survey |
| 19 | Frontend Modern Web UI | Responsive React 19 + TypeScript + Vite + TailwindCSS application | M4 | R3, Web Survey |
| 20 | Frontend Clipboard Paste (Ctrl+V) | Global paste listener capturing clipboard images and triggering instant conversion | M4 | R3, Web Survey |
| 21 | Frontend Multi-file Drag & Drop | Multi-file dropzone with card queue preview and multi-file processing status | M4 | R3, Web Survey |
| 22 | Frontend Mic Recording & Waveform Visualizer | Web Audio API recording to 16-bit PCM WAV with live HTML5 Canvas waveform animation | M4 | R3, Web Survey |
| 23 | Frontend Live Split-Screen Editor | CodeMirror 6 Markdown editor with synchronized scrolling with preview pane | M4 | R3, Web Survey |
| 24 | Frontend Math & Diagram Rendering | Live rendering with KaTeX (`$..$`, `$$..$$`), Mermaid.js diagrams, syntax highlighting | M4 | R3, Web Survey |
| 25 | Frontend One-Click Export | Export buttons for `.md` download, standalone styled HTML, and print/PDF generation | M4 | R3, Web Survey |
| 26 | Synthetic Multimodal Dataset Generation | Pure-Python generators for `/tests/data/` (tables/math images, 16kHz WAV, messy HTML) | E2E Track | R5, AI Survey |
| 27 | Opaque-box Test Suite (Tiers 1-4) | Comprehensive Category-Partition, Boundary, Pairwise, Real-World test suite | E2E Track | R5 |
| 28 | Interactive Browser E2E Test Suite | Automated Playwright tests for upload, Ctrl+V, WebSocket stream, and live editor preview | E2E Track | R5 |
| 29 | Final E2E 100% Pass Verification | Execute complete test suite against integrated full-stack app, 100% passing | M5 | R5, Project Pattern |
| 30 | Adversarial Coverage Hardening (Tier 5) | White-box adversarial testing with Challenger -> Worker -> Reviewer loop | M5 | Project Pattern |

*All 30 features have been assigned to specific milestones.*

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Architecture Baseline & Shared Specifications | Initialize git repo, monorepo dirs, author `/docs/specs/core_principles.md`, `/docs/specs/product_ux.md`, `/docs/specs/api_contract.yaml` | None | IN_PROGRESS (Worker: 18ca2d31-7230-45ba-ba52-c471e24ad25f) |
| M2 | Multimodal AI Pipelines Engine | Implement `/ai-pipelines/`: Vision OCR (tables + KaTeX), Voice STT (WAV, timestamps), Text Normalizer (tables, TOC, tags) | M1 | PLANNED |
| M3 | Backend Server & Real-time Streaming | Implement `/backend/`: FastAPI REST endpoints, WebSocket streaming, JobManager queue, secure temp handling | M1 | PLANNED |
| M4 | Frontend UI & Live Studio | Implement `/frontend/`: Vite + React + TailwindCSS, Ctrl+V paste, mic waveform visualizer, CodeMirror 6 live split editor, KaTeX/Mermaid | M1 | PLANNED |
| E2E | E2E Testing Track | Independent track: synthetic datasets in `/tests/data/`, Tiers 1-4 opaque-box tests, Playwright browser E2E, publish `TEST_READY.md` | M1 | PLANNED |
| M5 | Final Milestone: 100% E2E Pass & Hardening | Phase 1: Pass 100% of E2E tests (Tiers 1-4); Phase 2: Tier 5 Adversarial Coverage Hardening | M2, M3, M4, E2E | PLANNED |

---

## Interface Contracts

### `/ai-pipelines/` ↔ `/backend/`
- **Interface**: In-process asynchronous generators and Pydantic v2 data models.
- **Data Models**:
  - `ConversionOptions`: `extract_tables: bool`, `extract_math: bool`, `generate_toc: bool`, `extract_tags: bool`, `timestamp_silence_threshold: float`, `preferred_engine: str`
  - `PipelineResult`: `success: bool`, `pipeline: PipelineType`, `markdown: str`, `metadata: dict`, `warnings: list[str]`, `duration_ms: float`
  - `StreamChunk`: `event: str` ('status' | 'chunk' | 'complete' | 'error'), `job_id: str`, `delta: Optional[str]`, `progress: Optional[int]`, `message: Optional[str]`, `metadata: Optional[dict]`
- **Functions**:
  - `async def run_pipeline(file_path: Path, pipeline_type: PipelineType, options: ConversionOptions) -> PipelineResult`
  - `async def stream_pipeline(file_path: Path, pipeline_type: PipelineType, options: ConversionOptions) -> AsyncIterator[StreamChunk]`
- **Error Handling**: Custom exceptions `PipelineError`, `DegradedInputError`, `UnsupportedFormatError` caught by backend and translated to standard HTTP / WebSocket error frames.

### `/backend/` ↔ `/frontend/`
- **Interface**: OpenAPI 3.1.0 REST API & WebSocket.
- **REST Endpoints**:
  - `POST /api/v1/convert/file`: Multipart upload (`file`, `options_json`) -> returns `{ "job_id": "...", "status": "QUEUED" }`.
  - `POST /api/v1/convert/text`: JSON body (`raw_text`, `options`) -> returns direct `PipelineResult` or queued job.
  - `GET /api/v1/jobs/{job_id}`: Poll job status, metadata, and result if WebSocket unavailable.
  - `POST /api/v1/export/pdf`: Accepts Markdown, returns rendered PDF binary.
  - `GET /api/v1/health`: System status, active workers, GPU/engine availability.
- **WebSocket Protocol**:
  - Endpoint: `ws://localhost:8000/api/v1/ws/stream/{job_id}`
  - Frames (Client <- Server):
    * `{"event": "status", "stage": "ocr", "progress": 30, "message": "Extracting tables..."}`
    * `{"event": "chunk", "delta": "| Col 1 | Col 2 |\n|---|---|\n"}`
    * `{"event": "complete", "markdown": "...", "metadata": {...}}`
    * `{"event": "error", "code": "DEGRADED_IMAGE", "message": "..."}`

---

## Code Layout
```
d:\markdown tự code\
├── docs\
│   └── specs\
│       ├── core_principles.md
│       ├── product_ux.md
│       └── api_contract.yaml
├── ai-pipelines\
│   ├── vision_ocr\
│   │   ├── __init__.py
│   │   ├── ocr_engine.py
│   │   ├── table_extractor.py
│   │   └── math_extractor.py
│   ├── voice_stt\
│   │   ├── __init__.py
│   │   ├── stt_engine.py
│   │   └── segmenter.py
│   ├── text_engine\
│   │   ├── __init__.py
│   │   ├── normalizer.py
│   │   ├── toc_generator.py
│   │   └── tag_extractor.py
│   ├── schemas.py
│   └── pipeline_runner.py
├── backend\
│   ├── app\
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── routes\
│   │   │   ├── __init__.py
│   │   │   ├── convert.py
│   │   │   ├── stream.py
│   │   │   └── export.py
│   │   ├── services\
│   │   │   ├── __init__.py
│   │   │   ├── job_manager.py
│   │   │   └── temp_manager.py
│   │   └── websocket\
│   │       ├── __init__.py
│   │       └── connection_manager.py
│   ├── requirements.txt
│   └── run.py
├── frontend\
│   ├── src\
│   │   ├── components\
│   │   │   ├── Header.tsx
│   │   │   ├── IngestionZone.tsx
│   │   │   ├── WaveformVisualizer.tsx
│   │   │   ├── LiveEditor.tsx
│   │   │   ├── MarkdownPreview.tsx
│   │   │   └── ExportBar.tsx
│   │   ├── hooks\
│   │   │   ├── useAudioRecorder.ts
│   │   │   ├── useClipboardPaste.ts
│   │   │   └── useWebSocketStream.ts
│   │   ├── lib\
│   │   │   ├── api.ts
│   │   │   ├── katexPlugin.ts
│   │   │   └── mermaidRenderer.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
└── tests\
    ├── data\
    │   ├── vision\
    │   ├── audio\
    │   ├── text\
    │   └── generators\
    ├── unit\
    ├── integration\
    └── e2e\
```
