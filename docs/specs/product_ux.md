# DTAMarkdown Studio — Product UX Specification & Design System

**Specification Status**: Approved Baseline (M1)  
**Location**: `/docs/specs/product_ux.md`  
**Target Audience**: Frontend Engineers, UX/UI Designers, Full-Stack Engineers, QA/E2E Engineers  

---

## 1. Design Vision & Philosophy

**DTAMarkdown Studio** is an ultra-fast, professional multimodal conversion workbench designed for researchers, technical writers, software engineers, and knowledge workers. The user experience is built around three guiding pillars:

1. **Instant Frictionless Ingestion**: Paste anything (`Ctrl+V`), drag-and-drop any document, or speak naturally into the microphone without prior mode-switching.
2. **Real-Time Visual Transparency**: See converted Markdown streaming character-by-character while viewing live audio waveforms or conversion progress indicators.
3. **Synchronized Authoring Power**: Side-by-side editing and preview with synchronized scrolling, instant KaTeX math equations, Mermaid diagrams, and one-click multi-format exports.

---

## 2. Design System & Visual Tokens

The studio employs a modern, high-contrast, distraction-free aesthetic built with TailwindCSS.

### 2.1 Color Palette

| Token Category | Tailwind Class / Hex | Usage Description |
|---|---|---|
| **App Background** | `bg-slate-950` (`#020617`) | Main canvas background, deep dark ambiance |
| **Card / Surface** | `bg-slate-900` (`#0f172a`) | Ingestion zones, editor shells, modal dialogs |
| **Border / Divider** | `border-slate-800` (`#1e293b`) | Subtle dividers, card borders, editor splitters |
| **Primary Accent** | `bg-indigo-600` (`#4f46e5`) | Primary action buttons, active tab indicators |
| **Accent Hover** | `bg-indigo-500` (`#6366f1`) | Interactive hover state for accent elements |
| **Accent Glow** | `shadow-indigo-500/20` | Subtle focus rings and active recording halos |
| **Text Primary** | `text-slate-100` (`#f1f5f9`) | Primary headers, editor text, high-emphasis labels |
| **Text Secondary** | `text-slate-400` (`#94a3b8`) | Timestamps, metadata, placeholder text, captions |
| **Text Muted** | `text-slate-500` (`#64748b`) | Inactive shortcuts, disabled options, subtle counts |
| **Success State** | `text-emerald-400` / `bg-emerald-500/10` | Conversion complete, valid KaTeX formulas, copy success |
| **Warning State** | `text-amber-400` / `bg-amber-500/10` | Low contrast image, audio silence, partial OCR |
| **Destructive / Error**| `text-rose-400` / `bg-rose-500/10` | Processing error, delete draft, invalid syntax |
| **Audio Waveform** | `#818cf8` (Indigo 400) / `#c084fc` (Purple 400) | Dynamic canvas audio gradient during active recording |

### 2.2 Typography Hierarchy

- **System UI Font**: `Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
  * Clean, highly legible sans-serif for UI controls, navigation, and badges.
- **Code & Markdown Source Font**: `JetBrains Mono, Fira Code, Menlo, Monaco, Consolas, monospace`
  * Monospaced font with tabular numbers and ligatures for the CodeMirror editor pane.
- **Rendered Markdown Font**: `Inter` for body prose, with `KaTeX_Math` for LaTeX symbols.

---

## 3. Responsive Screen Layout & Wireframe Architecture

The studio follows a vertically stacked, desktop-optimized layout with responsive breakpoints:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│ [Logo] DTAMarkdown Studio    [Engines: PyMuPDF / Gemini / RapidOCR]   [Theme/Help]│  Header (48px)
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │               📥 Ingestion Zone (Drag & Drop or Ctrl+V)                  │   │  Ingestion Zone
│   │     [📷 Upload Document/Image]     [🎙️ Record Voice]     [📋 Paste Text]   │   │  (120px)
│   └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│   ┌───────────────────────────────┬─┬────────────────────────────────────────┐   │
│   │ 📝 Markdown Source (50%)      │┆│ 👁️ Live Preview (50%)                  │   │
│   │                               │┆│                                        │   │
│   │ # Sales Report 2026           │┆│ # Sales Report 2026                    │   │
│   │                               │┆│                                        │   │  Split-Screen
│   │ | Region | Target | Actual |  │┆│ ┌────────┬────────┬────────┐           │   │  Live Editor
│   │ |--------|--------|--------|  │┆│ │ Region │ Target │ Actual │           │   │  (Flex Fill)
│   │ | North  | $100k  | $115k  |  │┆│ ├────────┼────────┼────────┤           │   │
│   │                               │┆│ │ North  │ $100k  │ $115k  │           │   │
│   │ $$f(x) = \sum_{i=1}^n x_i$$   │┆│ └────────┴────────┴────────┘           │   │
│   │                               │┆│                                        │   │
│   │                               │┆│   f(x) = ∑ x_i                         │   │
│   │                               │┆│                                        │   │
│   └───────────────────────────────┴─┴────────────────────────────────────────┘   │
│                                                                                  │
├──────────────────────────────────────────────────────────────────────────────────┤
│ [Status: 🟢 Ready]  [342 words | 2 min read]        [Copy] [.md] [HTML] [PDF]   │  Export Dock (44px)
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Ingestion Zone: Multi-Format Interaction Specs

### 4.1 Global Clipboard Paste (`Ctrl+V` / `Cmd+V`)
- **Listener**: Registered at the root `window` level.
- **Handling Flow**:
  1. User presses `Ctrl+V` anywhere in the application.
  2. If the clipboard contains **image data** (`image/png`, `image/jpeg`, `image/webp`):
     - Prevents default paste event.
     - Creates an inline thumbnail preview in the Ingestion Zone.
     - Shows an immediate toast notification: `Image detected from clipboard — Starting Vision OCR...`.
     - Automatically fires `POST /api/v1/convert/file` with pipeline type `vision_ocr`.
     - Opens the WebSocket streaming connection and places focus on the editor.
  3. If the clipboard contains **HTML table or rich text**:
     - Automatically invokes the fast-path Text Normalization engine.
     - Shields KaTeX math delimiters and generates formatted GFM tables.
     - Injects clean Markdown directly into the active editor position.

### 4.2 Multi-File Drag-and-Drop Zone
- **Visual Feedback**:
  - `dragover`: Boundary switches from dashed `border-slate-700` to glowing `border-indigo-500` with an animated pulse background `bg-indigo-950/30`.
  - Drop prompt displays supported file icons: `PDF`, `PNG`, `JPG`, `WAV`, `MP3`, `TXT`, `HTML`.
- **Batch Card Queue**:
  - Dropping multiple files creates a horizontal scroll card queue beneath the dropzone.
  - Each file card displays:
    * File icon, filename, and file size.
    * Real-time progress bar (0% -> 100%).
    * Pipeline status pill (`QUEUED` [slate], `CONVERTING` [indigo-pulse], `COMPLETED` [emerald], `ERROR` [rose]).
  - Clicking a completed card immediately loads its Markdown into the Live Editor.

### 4.3 Microphone Voice Recording & Waveform Visualizer
- **Activation**: Clicking the `🎙️ Record Voice` button requests microphone access (`navigator.mediaDevices.getUserMedia`).
- **Real-Time Visual Feedback**:
  - The Ingestion Zone expands smoothly (`transition-all duration-300`) to reveal an HTML5 Canvas waveform dock (`height: 64px`, full width).
  - Web Audio API `AnalyserNode` streams live frequency/time-domain data.
  - The canvas renders a high-frame-rate (60 FPS) visualizer:
    * Idle / Low volume: A calm, undulating sine-wave ribbon with an indigo-to-purple linear gradient.
    * Active speaking: Vibrant dynamic frequency bars reacting to voice amplitude.
  - A glowing recording badge pulses red: `● REC 00:14`.
- **WAV Transcoding & Delivery**:
  - Audio is recorded in **16-bit Linear PCM WAV (16kHz mono)** via client-side AudioWorklet or lightweight script buffer.
  - Clicking `⏹️ Stop Recording`:
    * Finalizes WAV buffer and dispatches to `/api/v1/convert/file`.
    * WebSocket stream progressively writes transcript paragraphs with Markdown timestamp tags `**[HH:MM:SS]**`.

---

## 5. Live Split-Screen Editor: Synchronized Authoring Specs

### 5.1 Editor Pane (Left 50%)
- Powered by **CodeMirror 6**:
  - Monospace typography with syntax highlighting for Markdown headers, links, lists, bold/italics, and backticks.
  - Line numbers, active line highlight, and automatic bracket/quote closing.
  - Real-time streaming injection: As WebSocket `chunk` events arrive, new text appends smoothly at the current generation point without resetting user cursor position.
  - Undo/redo history maintained across streaming and manual edits.

### 5.2 Preview Pane (Right 50%)
- **Live GFM Rendering**:
  - Headers (`#`, `##`, `###`) styled with appropriate margins, subtle bottom borders on H1/H2, and automatic anchor links.
  - Tables rendered with rounded corners, alternating row zebra striping (`bg-slate-900/40`), padded cells, and horizontal scrollbars for wide columns.
- **KaTeX Math Rendering**:
  - Inline formulas `$E = mc^2$` rendered seamlessly within running prose.
  - Display formulas `$$\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}$$` rendered centered with comfortable padding.
  - KaTeX error boundary: Invalid LaTeX syntax renders in subtle red warning text (`KaTeX parse error: ...`) without crashing the entire preview pane.
- **Mermaid Diagrams**:
  - Code blocks tagged ````mermaid` are intercepted and rendered into scalable SVG diagrams.
  - Pan/zoom capabilities for large architectural flowcharts.

### 5.3 Synchronized Ratio Scrolling
- When the user scrolls the Editor pane, the Preview pane scrolls proportionally, and vice versa.
- **Loop Suppression Algorithm**:
  ```typescript
  let isSyncingLeft = false;
  let isSyncingRight = false;

  function onEditorScroll(e: Event) {
    if (isSyncingLeft) { isSyncingLeft = false; return; }
    isSyncingRight = true;
    const ratio = editor.scrollTop / (editor.scrollHeight - editor.clientHeight);
    preview.scrollTop = ratio * (preview.scrollHeight - preview.clientHeight);
  }

  function onPreviewScroll(e: Event) {
    if (isSyncingRight) { isSyncingRight = false; return; }
    isSyncingLeft = true;
    const ratio = preview.scrollTop / (preview.scrollHeight - preview.clientHeight);
    editor.scrollTop = ratio * (editor.scrollHeight - editor.clientHeight);
  }
  ```

---

## 6. Status & Export Dock Specifications

Fixed at the bottom of the viewport (`h-11`, `bg-slate-900/90`, backdrop-blur-md, `border-t border-slate-800`):

### 6.1 Status Telemetry
- **Engine Status Indicator**: Green pulse dot `🟢 Connected` with tooltip showing backend latency and active conversion engine (`PyMuPDF Fast-Path`, `Gemini Vision`, or `RapidOCR Offline`).
- **Document Statistics**: Live counters updated on every keystroke/chunk:
  * Word count (e.g., `420 words`)
  * Character count (e.g., `2,840 chars`)
  * Estimated reading time (e.g., `~2 min read`)

### 6.2 Export Actions
- **📋 Copy Markdown**:
  - Copies raw editor content to system clipboard.
  - Visual feedback: Button switches to `✓ Copied!` with `text-emerald-400` for 2 seconds.
- **⬇️ Export .md**:
  - Triggers client-side browser download of `{document_title}.md`.
- **🌐 Export HTML**:
  - Generates a standalone HTML file embedding KaTeX CSS, typography styling, and syntax highlighting stylesheets, ensuring self-contained offline viewing.
- **📄 Export PDF**:
  - Secondary dropdown offering:
    1. *Quick Print / PDF*: Launches browser print dialog with print-optimized stylesheet (`@media print` rules removing UI, expanding tables, avoiding orphan page breaks).
    2. *Server-Rendered PDF*: Sends `POST /api/v1/export/pdf` to obtain an official server-compiled PDF document.

---

## 7. Keyboard Shortcuts Map

| Shortcut | Action | Scope |
|---|---|---|
| `Ctrl+V` / `Cmd+V` | Smart paste (Image OCR / Table Normalizer) | Global |
| `Ctrl+S` / `Cmd+S` | Export as `.md` file | Global |
| `Ctrl+Shift+E` / `Cmd+Shift+E` | Trigger PDF Export | Global |
| `Ctrl+Enter` / `Cmd+Enter` | Toggle Voice Recording (Start / Stop) | Global |
| `Alt+Z` | Toggle Split-Screen / Full Editor / Full Preview | Global |
| `Ctrl+B` | Bold text (`**text**`) | Editor Pane |
| `Ctrl+I` | Italic text (`*text*`) | Editor Pane |
| `Ctrl+K` | Insert link (`[title](url)`) | Editor Pane |
| `Ctrl+M` | Insert KaTeX equation placeholder (`$$...$$`) | Editor Pane |
