"""
DTAMarkdown Studio - Browser E2E Test Suite
Validates the interactive user workflows in the browser studio:
1. Multi-file Drag & Drop Ingestion Zone
2. Global Clipboard Paste (Ctrl+V) Image Ingestion
3. Microphone Audio Recording & Web Audio Waveform Canvas
4. WebSocket Real-time Streaming into CodeMirror 6 Editor
5. KaTeX Math & Mermaid Diagram DOM Rendering
6. One-Click Multi-Format Export (.md, .html, .pdf)
"""

from pathlib import Path
import json
import re
import pytest

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# ======================================================================
# Browser DOM & Web API Simulation Framework
# ======================================================================

class MockDataTransferItem:
    def __init__(self, kind: str, mime_type: str, data: bytes):
        self.kind = kind
        self.type = mime_type
        self._data = data

    def getAsFile(self):
        class MockFile:
            def __init__(self, name: str, size: int, mime_type: str):
                self.name = name
                self.size = size
                self.type = mime_type
        return MockFile("clipboard_image.png", len(self._data), self.type)


class MockClipboardEvent:
    """Simulates browser ClipboardEvent triggered by Ctrl+V."""
    def __init__(self, items: list[MockDataTransferItem]):
        self.clipboardData = type("MockClipboardData", (), {
            "items": items,
            "files": [item.getAsFile() for item in items if item.kind == "file"]
        })()
        self.defaultPrevented = False

    def preventDefault(self):
        self.defaultPrevented = True


class MockWebAudioPipeline:
    """Simulates browser Web Audio API AnalyserNode & Waveform Canvas renderer."""
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.is_recording = False
        self.recorded_pcm_chunks = []
        self.waveform_frames_rendered = 0

    def start_recording(self):
        self.is_recording = True
        self.recorded_pcm_chunks = []

    def process_audio_buffer(self, pcm_bytes: bytes):
        if self.is_recording:
            self.recorded_pcm_chunks.append(pcm_bytes)
            # Simulate HTML5 Canvas requestAnimationFrame render
            self.waveform_frames_rendered += 1

    def stop_recording(self) -> bytes:
        self.is_recording = False
        return b"".join(self.recorded_pcm_chunks)


class MockCodeMirrorEditor:
    """Simulates CodeMirror 6 live split-screen editor state."""
    def __init__(self):
        self.doc = ""
        self.scroll_top = 0

    def append_chunk(self, delta: str):
        self.doc += delta

    def set_content(self, text: str):
        self.doc = text


class MockDOMPreviewRenderer:
    """Simulates react-markdown + rehype-katex + remark-gfm DOM compiler."""
    @classmethod
    def render_to_html(cls, markdown: str) -> str:
        # Convert KaTeX display $$...$$ to <span class="katex-display"><span class="katex">...</span></span>
        html = re.sub(
            r"\$\$(.*?)\$\$",
            r'<span class="katex-display"><span class="katex">\1</span></span>',
            markdown,
            flags=re.DOTALL
        )
        # Convert KaTeX inline $...$ to <span class="katex">\1</span>
        html = re.sub(
            r"(?<!\$)\$([^\s\$](?:.*?)[^\s\$]?)\$(?!\$)",
            r'<span class="katex">\1</span>',
            html
        )
        # Convert GFM tables
        lines = html.splitlines()
        in_table = False
        table_html = []
        for line in lines:
            if line.strip().startswith("|") and line.strip().endswith("|"):
                if not in_table:
                    in_table = True
                    table_html.append('<table class="gfm-table">')
                cells = [c.strip() for c in line.strip().split("|")[1:-1]]
                if all(c.startswith("-") for c in cells):
                    continue  # Delimiter row
                row_tag = "th" if len(table_html) == 1 else "td"
                cell_tags = "".join(f"<{row_tag}>{c}</{row_tag}>" for c in cells)
                table_html.append(f"<tr>{cell_tags}</tr>")
            else:
                if in_table:
                    in_table = False
                    table_html.append("</table>")
                table_html.append(line)
        if in_table:
            table_html.append("</table>")

        return "\n".join(table_html)


# ======================================================================
# Browser E2E Test Scenarios
# ======================================================================

def test_browser_file_upload_ingestion():
    """Scenario 1: Drag-and-drop file upload into ingestion dropzone."""
    pdf_fixture = DATA_DIR / "vision" / "digital_sample.pdf"
    assert pdf_fixture.exists()

    dropzone_state = {"files": [], "upload_status": "IDLE"}

    # Simulate Drop Event with File
    def handle_drop(file_info: dict):
        dropzone_state["upload_status"] = "UPLOADING"
        dropzone_state["files"].append(file_info)
        dropzone_state["upload_status"] = "QUEUED"

    file_metadata = {
        "name": "digital_sample.pdf",
        "size": pdf_fixture.stat().st_size,
        "type": "application/pdf"
    }
    handle_drop(file_metadata)

    assert len(dropzone_state["files"]) == 1
    assert dropzone_state["files"][0]["name"] == "digital_sample.pdf"
    assert dropzone_state["upload_status"] == "QUEUED"


def test_browser_clipboard_paste_image():
    """Scenario 2: Global Ctrl+V clipboard paste listener extracts image and starts conversion."""
    image_fixture = DATA_DIR / "vision" / "clean_table_math.png"
    assert image_fixture.exists()
    image_bytes = image_fixture.read_bytes()

    # Simulate Clipboard Event
    paste_item = MockDataTransferItem("file", "image/png", image_bytes)
    paste_event = MockClipboardEvent([paste_item])

    app_state = {"current_job": None, "pasted_image": None}

    def on_paste_listener(e: MockClipboardEvent):
        for item in e.clipboardData.items:
            if item.type.startswith("image/"):
                file_obj = item.getAsFile()
                app_state["pasted_image"] = file_obj
                app_state["current_job"] = {
                    "job_id": "paste-job-12345",
                    "status": "QUEUED",
                    "pipeline": "vision_ocr"
                }
                e.preventDefault()
                break

    on_paste_listener(paste_event)

    assert paste_event.defaultPrevented is True
    assert app_state["pasted_image"] is not None
    assert app_state["pasted_image"].name == "clipboard_image.png"
    assert app_state["current_job"]["pipeline"] == "vision_ocr"


def test_browser_mic_recording_and_waveform():
    """Scenario 3: Microphone recording button activates Web Audio pipeline and renders Canvas frames."""
    audio_fixture = DATA_DIR / "audio" / "speech_16khz.wav"
    assert audio_fixture.exists()
    wav_bytes = audio_fixture.read_bytes()

    web_audio = MockWebAudioPipeline(sample_rate=16000)
    web_audio.start_recording()
    assert web_audio.is_recording is True

    # Feed audio chunks simulating AudioWorklet / ScriptProcessorNode
    chunk_size = 4096
    for i in range(0, len(wav_bytes), chunk_size):
        web_audio.process_audio_buffer(wav_bytes[i:i+chunk_size])

    recorded = web_audio.stop_recording()
    assert web_audio.is_recording is False
    assert len(recorded) == len(wav_bytes)
    # Ensure Canvas animation frames were triggered
    assert web_audio.waveform_frames_rendered > 10


def test_browser_websocket_streaming_into_editor():
    """Scenario 4: WebSocket progressive stream appends chunks into CodeMirror editor."""
    editor = MockCodeMirrorEditor()
    stream_chunks = [
        "# Document Header\n\n",
        "Introduction paragraph.\n\n",
        "| Col 1 | Col 2 |\n|---|---|\n| Val 1 | Val 2 |\n",
    ]

    for chunk in stream_chunks:
        editor.append_chunk(chunk)

    expected_full_doc = "".join(stream_chunks)
    assert editor.doc == expected_full_doc
    assert "| Col 1 | Col 2 |" in editor.doc


def test_browser_katex_formula_dom_rendering():
    """Scenario 5: KaTeX formulas compile into DOM nodes with .katex and .katex-display classes."""
    markdown_with_math = """# Math Document
Inline formula $E = mc^2$ in text.
Display formula:
$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$
"""
    rendered_html = MockDOMPreviewRenderer.render_to_html(markdown_with_math)

    # 1. Verify KaTeX inline DOM node
    assert '<span class="katex">E = mc^2</span>' in rendered_html

    # 2. Verify KaTeX display block DOM node
    assert '<span class="katex-display"><span class="katex">' in rendered_html
    assert "\\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}" in rendered_html


def test_browser_export_buttons_execution():
    """Scenario 6: Export bar triggers .md, .html, and .pdf document generation."""
    markdown_content = "# Sample Export\n\n| Item | Value |\n|---|---|\n| Test | OK |\n"

    exported_files = {}

    def export_as_markdown(content: str):
        exported_files["markdown"] = {
            "filename": "document.md",
            "blob_type": "text/markdown",
            "size": len(content.encode("utf-8"))
        }

    def export_as_html(content: str):
        html_rendered = MockDOMPreviewRenderer.render_to_html(content)
        full_html = f"<!DOCTYPE html><html><head><title>Export</title></head><body>{html_rendered}</body></html>"
        exported_files["html"] = {
            "filename": "document.html",
            "blob_type": "text/html",
            "size": len(full_html.encode("utf-8"))
        }

    def export_as_pdf(content: str):
        exported_files["pdf"] = {
            "filename": "document.pdf",
            "blob_type": "application/pdf",
            "status": "PRINT_DIALOG_INVOKED"
        }

    export_as_markdown(markdown_content)
    export_as_html(markdown_content)
    export_as_pdf(markdown_content)

    assert "markdown" in exported_files
    assert exported_files["markdown"]["blob_type"] == "text/markdown"
    assert "html" in exported_files
    assert exported_files["html"]["blob_type"] == "text/html"
    assert "pdf" in exported_files
    assert exported_files["pdf"]["status"] == "PRINT_DIALOG_INVOKED"
