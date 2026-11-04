# DTAMarkdown Studio — Core Architectural Principles

**Specification Status**: Approved Baseline (M1)  
**Location**: `/docs/specs/core_principles.md`  
**Target Audience**: Multimodal AI Engineers, Backend Engineers, Frontend Engineers, QA Engineers  

---

## 1. Executive Summary

DTAMarkdown Studio is a production full-stack system designed to convert multimodal unstructured inputs (document scans, high-resolution and degraded images, voice/audio recordings, messy HTML, and raw text) into pristine, structurally compliant GitHub Flavored Markdown (GFM) with rich KaTeX math, Mermaid diagrams, and preserved tabular hierarchies.

To guarantee high availability, cross-platform reproducibility, sub-second interactive feedback, and zero resource leaks, every component in this monorepo must strictly adhere to the **Six Core Architectural Principles** detailed herein.

---

## 2. The Six Core Architectural Principles

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       DTAMarkdown Core Principles                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Contract-First Architecture (OpenAPI 3.1 & Pydantic v2 Sync)            │
│  2. Non-Blocking Real-Time Streaming (Async Generators & WebSockets)        │
│  3. Zero Data Leakage & Deterministic Tempfile Lifecycle                    │
│  4. Zero-CLI Binary Dependency (Pure Python / ONNX / Web Standards)         │
│  5. KaTeX Math & Table Structural Integrity                                 │
│  6. Graceful Multi-Tier Degradation & Fault Tolerance                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Principle 1: Contract-First Architecture

#### 1.1 Specification Authority
- No implementation code (REST endpoints, WebSocket event handlers, or frontend API clients) may be written before its interface is formally specified in `/docs/specs/api_contract.yaml`.
- The OpenAPI 3.1.0 specification serves as the **single source of truth** across frontend, backend, and automated testing tracks.

#### 1.2 Type Safety & Schema Synchronization
- **Backend**: Every request body, query parameter, and response payload in FastAPI must bind directly to Pydantic v2 schemas located in `/ai-pipelines/schemas.py` and `/backend/app/schemas/`. Manual JSON parsing without validation is prohibited.
- **Frontend**: TypeScript interfaces in `/frontend/src/types/api.ts` must mirror the OpenAPI schema definitions verbatim.
- **Streaming Contracts**: The WebSocket channel (`/api/v1/ws/stream/{job_id}`) enforces an immutable frame protocol:
  * `status`: Progress percentage, operational stage name, human-readable message.
  * `chunk`: Incremental Markdown delta string (`delta`).
  * `complete`: Final accumulated Markdown document, metadata summary (word count, duration, tags).
  * `error`: Standardized error code, actionable diagnostic message, and recoverable flag.

---

### Principle 2: Non-Blocking Real-Time Streaming

#### 2.1 Latency-First User Experience
- Heavy multimodal conversions (OCR and audio transcription) can take anywhere from 800ms to 8 seconds. Users must **never** be blocked waiting for a monolithic HTTP response.
- From the moment an ingestion task starts, the backend must initiate progressive chunk streaming via WebSockets within **≤ 250ms** of initial token generation.

#### 2.2 Asynchronous Pipeline Generators
- AI pipelines must expose asynchronous generators:
  ```python
  async def stream_pipeline(
      file_path: Path,
      pipeline_type: PipelineType,
      options: ConversionOptions
  ) -> AsyncIterator[StreamChunk]:
      ...
  ```
- Long-running CPU-bound or GPU-bound operations (e.g., PyMuPDF rendering, ONNX inference, audio decoding) must execute in thread pools using `asyncio.to_thread` or non-blocking event loops, preventing the FastAPI main thread from dropping concurrent WebSocket heartbeats.

#### 2.3 Resilient Connection Lifecycle
- If a client disconnects (`WebSocketDisconnect`), background job execution continues detached for at least 60 seconds so the client can reconnect or retrieve the final result via polling `GET /api/v1/jobs/{job_id}`. If neither reconnect nor poll occurs within this 60-second grace window, the backend signals a `cancellation_event` to the pipeline worker, aborting downstream inference and releasing memory.
- If a client fails to connect via WebSocket (e.g., corporate proxy blocking WS), the system provides an asynchronous polling fallback via `GET /api/v1/jobs/{job_id}`.

---

### Principle 3: Zero Data Leakage & Deterministic Tempfile Lifecycle

#### 3.1 File Isolation & Staging Sandbox
- Uploaded multi-megabyte files (PDFs, TIFFs, WAVs) must never be written to random working directories or committed to source control.
- All uploads must reside in a dedicated staging directory: `tempfile.gettempdir() / "dtamarkdown_staging"`.
- File paths are strictly generated using cryptographically random UUIDv4 identifiers: `{job_id}_{timestamp}_{sanitized_basename}`.
- Path traversal sequences (`../`, `..\\`) must be stripped during filename sanitization.

#### 3.2 Immediate Context-Managed Cleanup
- File handlers must use context managers (`ManagedTempFile`) ensuring deterministic file unlinking in a `finally` block:
  ```python
  async with ManagedTempFile(upload_file) as staged_path:
      async for chunk in stream_pipeline(staged_path, ...):
          yield chunk
  # staged_path is guaranteed unlinked here, even if exceptions occur
  ```

#### 3.3 Autonomous Background Sweeper (Reaper)
- An asynchronous background task (`TempReaperService`) boots with the FastAPI server and runs every **10 minutes**.
- The sweeper scans `dtamarkdown_staging` and forcibly deletes any orphaned files whose last modification time exceeds **30 minutes**, ensuring 0% disk accumulation over long uptimes.

#### 3.4 Startup Staging Sweep
- During FastAPI lifespan startup, `TempReaperService` executes an immediate synchronous sweep of `dtamarkdown_staging` to purge or quarantine any orphaned files remaining from previous unexpected process crashes.

---

### Principle 4: Zero-CLI Binary Dependency

#### 4.1 The Windows Environment Reality
- Host systems and developer laptops frequently lack system-level C++ executables such as `ffmpeg.exe`, `ffprobe.exe`, `tesseract.exe`, `pandoc.exe`, or `wkhtmltopdf.exe`.
- **Hard Rule**: The backend and AI pipelines must **NEVER** invoke `subprocess.run(["ffmpeg", ...])` or `subprocess.run(["tesseract", ...])` without providing a pure Python/in-process fallback. Relying on missing external system binaries is an architectural defect.

#### 4.2 Voice STT Solution (Pure WAV / Web Standards)
- Audio ingestion standardizes on **16-bit Linear PCM WAV (16,000 Hz, Mono)**.
- Frontend microphone recording captures audio and transcodes to standard WAV chunks client-side via Web Audio API (`AudioContext` / `AudioWorklet`), bypassing any need for server-side `ffmpeg`.
- Server-side audio reading uses Python's standard `wave` library, `audioop-lts`, `standard-aifc`, and `SpeechRecognition` / `faster-whisper` direct buffers.

#### 4.3 Vision OCR Solution (Pure ONNX / MuPDF / Cloud Fallback)
- Digital PDFs: Extracted via `PyMuPDF` (`fitz`), which embeds pre-compiled MuPDF C libraries into its Python wheel.
- Scanned Images: Handled by `rapidocr-onnxruntime` (which bundles lightweight ONNX models executed by `onnxruntime` without external C++ software) or high-fidelity Multimodal Vision API (Gemini Vision) via REST.

---

### Principle 5: KaTeX Math & Table Structural Integrity

#### 5.1 GFM Table Structural Rules
- Standard Markdown tables must maintain rigid column-count symmetry:
  * Header row count must match delimiter separator count: `| A | B | C |` -> `|---|---|---|`.
  * Data rows must never contain mismatched cell counts. Missing cells must be padded with whitespace `|   |`.
  * Internal pipe characters (`|`) inside text, equations, or code cells must be escaped (`\|`).
  * Newline characters inside table cells must be converted to `<br>` tags to prevent breaking table row parsing.

#### 5.2 Mathematical Formula Shielding (MathShield)
- Mathematical equations must be delimited according to KaTeX standards:
  * Inline formulas: `$equation$` (no leading or trailing whitespace immediately inside the dollars).
  * Display block formulas: `$$\nequation\n$$`.
- When converting HTML or unstructured text to Markdown, math expressions frequently get corrupted (e.g. `x_1 * x_2` interpreted as italics `x<i>1 * x</i>2`, or `a < b` interpreted as HTML tags).
- All conversion pipelines must employ a two-phase **MathShield** mechanism:
  1. *Shield Phase*: Replace `$..$` and `$$..$$` with inert cryptographic tokens (e.g. `__MATH_SHIELD_INLINE_0__`).
  2. *Transformation Phase*: Execute HTML cleaning, table formatting, and whitespace normalization.
  3. *Unshield Phase*: Restore original pristine LaTeX strings back into the Markdown stream.

#### 5.3 KaTeX Syntax Verification
- Formulas extracted by OCR or text pipelines must undergo delimiter pairing validation. Any unclosed `$` or `$$` must be corrected or flagged with a warning rather than corrupting the preview parser.

---

### Principle 6: Graceful Multi-Tier Degradation & Fault Tolerance

#### 6.1 Multi-Tier Engine Fallback Hierarchy
Every conversion domain must implement a graceful fallback matrix:

| Domain | Tier 1 (Primary / Fast-Path) | Tier 2 (High-Fidelity) | Tier 3 (Offline / Baseline) |
|---|---|---|---|
| **Digital PDF** | PyMuPDF text/table extraction (<50ms) | Gemini Vision API | RapidOCR ONNX |
| **Scanned Doc / Image** | Gemini Vision API (if API key present) | RapidOCR ONNX Runtime | MarkItDown layout parser |
| **Audio / Voice** | Gemini Multimodal Audio API | faster-whisper (local quantized) | SpeechRecognition / Google STT |
| **PDF Export** | Browser `@media print` CSS | Server-side PyMuPDF / Weasyprint | Raw HTML printable template |

#### 6.2 Defensive Boundary Handling
- Corrupted, 0-byte, or degraded inputs must **never** trigger unhandled 500 Internal Server Errors or crash background workers.
- The pipeline must detect:
  * Degraded / Low-contrast images -> Output available text with a Markdown warning callout: `> [!WARNING] Low image contrast detected.`
  * Silent / 0-byte audio -> Return clean empty transcript with status `NO_SPEECH_DETECTED`.
  * XSS / Malformed HTML -> Sanitize dangerous tags (`<script>`, `<iframe`, `onerror=`) while preserving text and structure.

---

## 3. Compliance & Verification Criteria

1. **Static Analysis**: All backend and AI pipeline code must pass linting and type checking with zero untyped API boundaries.
2. **Deterministic Cleanup Test**: Automated tests in `/tests/integration/` must verify that `dtamarkdown_staging` has 0 residual files after 50 consecutive conversion cycles.
3. **No-CLI Dependency Verification**: The entire suite must execute and pass on an environment where `ffmpeg` and `tesseract` are completely absent from PATH.
4. **Table & Math Integrity Assertion**: Markdown preview test suite must verify that 100% of generated tables render with valid GFM headers and 100% of equations render without KaTeX parse crashes.
