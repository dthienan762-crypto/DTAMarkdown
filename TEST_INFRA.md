# DTAMarkdown Studio — Test Infrastructure & Quality Engineering Specification

**Document Version**: 1.0.0  
**Status**: APPROVED BASELINE  
**Author**: QA & E2E Testing Track (`teamwork_test_writer_e2e`)  
**Scope**: `/tests/`, Multimodal AI Pipelines, Backend Server, WebSocket Streaming, Frontend Live Studio

---

## 1. Test Philosophy

DTAMarkdown Studio's test architecture is built on three foundational pillars: **Opaque-Box Verification**, **Requirement-Driven Traceability**, and **Progressive Testability**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Quality Engineering Tenets                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Opaque-Box Execution: Tests validate observable contracts (REST APIs,   │
│     WebSockets, GFM output, KaTeX renderability) without white-box coupling.│
│  2. Deterministic & Self-Contained: Zero external binary dependencies;      │
│     all fixtures are synthesized programmatically in pure Python.           │
│  3. Progressive Testability: Test tiers cleanly isolate feature readiness   │
│     and gracefully adapt between in-memory mock drivers and live services.  │
│  4. Zero Data Leakage: Mandatory verification that temporary upload stages  │
│     are cleaned up with zero disk persistence across test runs.             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The 4-Tier Test Methodology

Every functional requirement from `ORIGINAL_REQUEST.md` and feature in `PROJECT.md` is verified through a four-tier testing hierarchy:

```
                      ┌─────────────────────────────────┐
                      │ Tier 4: Real-World Scenarios    │
                      │ (Academic, Medical, Meeting)    │
                      ├─────────────────────────────────┤
                      │ Tier 3: Combinations & Stress   │
                      │ (Table+Math, Audio+Silence)     │
                      ├─────────────────────────────────┤
                      │ Tier 2: Boundaries & Corners    │
                      │ (0-byte, Corrupt, >50MB, UTF-8) │
                      ├─────────────────────────────────┤
                      │ Tier 1: Core Feature Coverage   │
                      │ (≥5 tests per primary feature)  │
                      └─────────────────────────────────┘
```

### Tier 1: Core Feature Coverage (`tests/test_tier1_features.py`)
- Exhaustive verification of core capabilities defined in R1 & R2:
  * **Feature 5 & 11 (Table Parsing & Normalization)**: Column count symmetry, cell padding, pipe escaping (`\|`), colspan/rowspan resolution.
  * **Feature 6 & 12 (KaTeX Math Extraction & MathShield)**: Inline `$..$` and display `$$..$$` syntax validation, bracket matching, collision shielding during text operations.
  * **Feature 8, 9 & 10 (Voice STT & Timestamps)**: 16-bit PCM WAV (16kHz) ingestion, automatic punctuation, silence-gap detection (>2.0s), Markdown timestamp headers `**[HH:MM:SS]**`.
  * **Feature 13 (TOC Generation)**: Markdown heading extraction (`#` to `######`), GitHub anchor slugification, relative indentation.
  * **Feature 14 (Tag & Metadata Extraction)**: Keyword extraction, word count, read time, YAML frontmatter formatting.
  * **Rule**: Every primary feature has **at least 5 independent tests**.

### Tier 2: Boundary & Corner Cases (`tests/test_tier2_boundaries.py`)
- Defensive testing against real-world degraded, corrupted, and hostile inputs:
  * **Empty & 0-Byte Payloads**: `empty_0byte.png`, `empty_audio.wav`, empty text strings return structured 400 Bad Request or `NO_SPEECH_DETECTED` status, never 500 crashes.
  * **Corrupt Non-Audio / Non-Image Data**: Random byte streams return 415 Unsupported Media Type or graceful fallback with diagnostic error codes.
  * **Payload Size Limits**: Verification of 413 Payload Too Large for files exceeding 50MB (documents/images) and 100MB (audio).
  * **Unclosed Math Delimiters**: Lone `$` or dangling `$$` must not crash preview parser or cascade errors into downstream text.
  * **Special Unicode Characters**: Zero-width spaces (`\u200B`), non-breaking spaces (`\u00A0`), bidirectional marks, smart quotes.
  * **Deeply Nested & Broken Tables**: Unclosed `<tr>`, nested `<table>` tags inside table cells without stack overflows.

### Tier 3: Cross-Feature Combinations (`tests/test_tier3_combinations.py`)
- Interaction and pairwise testing across multiple simultaneous features:
  * **Multimodal Image**: Image with both complex tabular grid AND inline/block KaTeX formulas.
  * **Speech Audio with Technical Terms & Long Pauses**: Multi-paragraph transcript containing mathematical terms and silence pauses (>2.0s) triggering timestamp annotations.
  * **HTML with Tables, Code Blocks, and Math**: HTML documents containing code snippets (`<code>`), formulas, and broken tables transformed without delimiter cross-contamination.
  * **WebSocket Streaming + Cancellation**: Progressive chunk accumulation (`status` -> `chunk` -> `complete`) and clean disconnection handling (`WebSocketDisconnect`).

### Tier 4: Real-World Application Scenarios (`tests/test_tier4_realworld.py`)
- End-to-end composite scenarios simulating authentic user workflows:
  * **Scenario 1 (Academic Research Paper Page)**: Abstract, multi-level headings, Gaussian probability density function `$$f(x)$$`, and architecture comparison table.
  * **Scenario 2 (Medical Clinic Invoice Table)**: Low-contrast, noisy scan with CPT procedure codes, line items, monetary amounts, and dosage adjustment formula `$$D_{adj}$$`.
  * **Scenario 3 (Multi-Speaker Technical Meeting Transcript)**: Audio recording segments converted into chronological speaker blocks with timestamps.
  * **Scenario 4 (Complex GitHub Wiki / Technical Documentation)**: Deep headings, table of contents, tags, callout blocks, and syntax-highlighted code.

---

## 3. Feature Inventory to Test Tier Mapping

| # | Feature Name | Primary Milestone | Test Suite & Tier | Verification Target |
|---|--------------|-------------------|-------------------|---------------------|
| 1 | Monorepo & Git Setup | M1 | `test_specs_contract.py` | Directory structure, .gitignore |
| 2 | Core Principles Spec | M1 | `test_m1_adversarial_challenge.py` | 6 Principles, Tempfile lifecycle |
| 3 | Product UX Spec | M1 | `test_m1_adversarial_challenge.py` | UI layout tokens, states |
| 4 | OpenAPI 3.1 & WS Contract | M1 | `test_specs_contract.py` | All endpoints, schemas, refs |
| 5 | Vision OCR - Table Extraction | M2 | `test_tier1_features.py` (Tier 1) | GFM table symmetry & alignment |
| 6 | Vision OCR - Math Extraction | M2 | `test_tier1_features.py` (Tier 1) | KaTeX `$..$` & `$$..$$` syntax |
| 7 | Vision OCR - Multi-tier Fallback | M2 | `test_tier2_boundaries.py` (Tier 2) | PyMuPDF -> Gemini -> RapidOCR |
| 8 | Voice STT - Audio Transcription | M2 | `test_tier1_features.py` (Tier 1) | Speech transcription & punctuation |
| 9 | Voice STT - Timestamps & Paragraphs | M2 | `test_tier1_features.py` (Tier 1) | Silence gap (>2.0s), `**[HH:MM:SS]**` |
| 10 | Voice STT - Direct 16-bit PCM WAV | M2 | `test_tier1_features.py` (Tier 1) | 16kHz WAV ingestion, zero ffmpeg |
| 11 | Text Engine - HTML & Table Normalization | M2 | `test_tier1_features.py` (Tier 1) | Table flattening, pipe escaping |
| 12 | Text Engine - MathShield | M2 | `test_tier1_features.py` (Tier 1) | Protect LaTeX during HTML parsing |
| 13 | Text Engine - Automatic TOC | M2 | `test_tier1_features.py` (Tier 1) | Hierarchy & GitHub anchor slugs |
| 14 | Text Engine - Tag & Metadata Extraction | M2 | `test_tier1_features.py` (Tier 1) | Keywords, word count, frontmatter |
| 15 | FastAPI Server & REST Endpoints | M3 | `test_tier1_features.py` (Tier 1) | Conformance to `api_contract.yaml` |
| 16 | WebSocket Real-time Streaming | M3 | `test_tier3_combinations.py` (Tier 3) | Chunk ordering & frame schemas |
| 17 | Async Queue & Job Manager | M3 | `test_tier3_combinations.py` (Tier 3) | Semaphore bounding, job state flow |
| 18 | Secure Staging & Temp Reaper | M3 | `test_tier2_boundaries.py` (Tier 2) | UUID tempfile unlinking, zero leaks |
| 19 | Frontend Modern Web UI | M4 | `tests/e2e/test_browser_studio.py` | Responsive React + Tailwind UI |
| 20 | Frontend Clipboard Paste (Ctrl+V) | M4 | `tests/e2e/test_browser_studio.py` | Clipboard image paste trigger |
| 21 | Frontend Drag & Drop Ingestion | M4 | `tests/e2e/test_browser_studio.py` | Dropzone file upload workflow |
| 22 | Frontend Mic & Waveform Visualizer | M4 | `tests/e2e/test_browser_studio.py` | Audio recording & Canvas animation |
| 23 | Frontend Live Split-Screen Editor | M4 | `tests/e2e/test_browser_studio.py` | CodeMirror sync scroll |
| 24 | Frontend Math & Diagram Rendering | M4 | `tests/e2e/test_browser_studio.py` | KaTeX & Mermaid DOM rendering |
| 25 | Frontend One-Click Export | M4 | `tests/e2e/test_browser_studio.py` | `.md`, `.html`, `.pdf` downloads |
| 26 | Synthetic Multimodal Datasets | E2E | `tests/data/generate_datasets.py` | Pure-Python fixtures generated |
| 27 | Opaque-box Test Suite (Tiers 1-4) | E2E | `test_tier1_*.py` to `test_tier4_*.py` | 100% test pass verification |
| 28 | Interactive Browser E2E Suite | E2E | `tests/e2e/test_browser_studio.py` | Playwright workflow simulation |
| 29 | Final E2E 100% Pass Verification | M5 | Full Suite Runner | 100% test pass on live stack |
| 30 | Adversarial Coverage Hardening | M5 | Challenger-Reviewer Loop | White-box stress & fuzzing |

---

## 4. Test Architecture & Runner Setup

### 4.1 Directory Organization
```
tests/
├── data/
│   ├── generate_datasets.py         # Pure-Python synthetic fixture generator
│   ├── vision/                      # Clean table/math, degraded scan, vector PDF, 0-byte
│   ├── audio/                       # 16kHz PCM WAV speech, 0-byte, corrupt audio
│   ├── text/                        # Messy HTML, markdown breakcases
│   └── expected/                    # Golden baseline expected Markdown files
├── e2e/
│   └── test_browser_studio.py       # Playwright browser end-to-end suite
├── test_specs_contract.py           # Milestone 1 OpenAPI spec validity
├── test_m1_adversarial_challenge.py # Milestone 1 Edge cases & spec stress
├── test_tier1_features.py           # Tier 1 Feature coverage tests (≥5 per feature)
├── test_tier2_boundaries.py         # Tier 2 Boundary & defensive tests
├── test_tier3_combinations.py       # Tier 3 Cross-feature combination tests
└── test_tier4_realworld.py          # Tier 4 Real-world domain scenario tests
```

### 4.2 Execution Commands
```powershell
# 1. Regenerate synthetic multimodal datasets:
python tests/data/generate_datasets.py

# 2. Run all Tier 1-4 tests:
python -m pytest tests/test_tier1_features.py tests/test_tier2_boundaries.py tests/test_tier3_combinations.py tests/test_tier4_realworld.py -v

# 3. Run complete test suite (Specs + Contract + Tiers 1-4):
python -m pytest tests/ -v

# 4. Run browser E2E test suite (when frontend dev server is running):
python -m pytest tests/e2e/test_browser_studio.py -v
```

### 4.3 Coverage & Quality Thresholds
1. **Pass Rate**: 100% passing tests (0 failures, 0 unhandled exceptions).
2. **Schema Integrity**: Every REST & WebSocket payload must pass Pydantic validation against `docs/specs/api_contract.yaml`.
3. **Table Integrity**: 100% of tested Markdown tables must have matching column counts across header and data rows.
4. **KaTeX Integrity**: 100% of inline (`$`) and display (`$$`) delimiters must be paired; zero unescaped collisions with Markdown asterisks/underscores.
5. **Zero Data Leakage**: Ingestion temporary files must be cleaned up immediately, with zero persistent files in staging.
