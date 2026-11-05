"""
Unit tests for Unified Pipeline Runner (/ai-pipelines/pipeline_runner.py)
Validates async run_pipeline, stream_pipeline, auto-detection, and exception flows.
"""

import asyncio
from pathlib import Path
import struct
import sys
import tempfile
import wave
import pytest

PIPELINES_DIR = Path(__file__).resolve().parent.parent
if str(PIPELINES_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINES_DIR))

from schemas import ConversionOptions, EmptyFileError, PipelineType, UnsupportedFormatError
from pipeline_runner import (
    PipelineRunner,
    detect_pipeline_type,
    run_pipeline,
    stream_pipeline,
)
import pymupdf


def test_detect_pipeline_type():
    assert detect_pipeline_type(Path("sample.pdf")) == PipelineType.VISION_OCR
    assert detect_pipeline_type(Path("photo.png")) == PipelineType.VISION_OCR
    assert detect_pipeline_type(Path("recording.wav")) == PipelineType.VOICE_STT
    assert detect_pipeline_type(Path("page.html")) == PipelineType.TEXT_NORMALIZE
    assert detect_pipeline_type(Path("document.txt")) == PipelineType.TEXT_NORMALIZE

    with pytest.raises(UnsupportedFormatError):
        detect_pipeline_type(Path("archive.xyz"))


@pytest.mark.anyio
async def test_run_pipeline_text_normalize():
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as tf:
        tf.write("<h1>Sample Title</h1><p>Test text with formula: $a^2 + b^2 = c^2$.</p>")
        temp_html = Path(tf.name)

    try:
        options = ConversionOptions(generate_toc=True, extract_tags=True)
        result = await run_pipeline(temp_html, pipeline_type=PipelineType.TEXT_NORMALIZE, options=options)

        assert result.success is True
        assert result.pipeline == PipelineType.TEXT_NORMALIZE
        assert "Sample Title" in result.markdown
        assert "$a^2 + b^2 = c^2$" in result.markdown
        assert result.duration_ms > 0
    finally:
        if temp_html.exists():
            temp_html.unlink()


@pytest.mark.anyio
async def test_stream_pipeline_text_normalize():
    with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8") as tf:
        tf.write("<h1>Overview</h1><p>Paragraph 1.</p><p>Paragraph 2.</p>")
        temp_html = Path(tf.name)

    try:
        chunks = []
        async for chunk in stream_pipeline(temp_html, pipeline_type=PipelineType.TEXT_NORMALIZE):
            chunks.append(chunk)

        assert len(chunks) >= 3  # status, chunk(s), complete
        events = [c.event for c in chunks]
        assert "status" in events
        assert "chunk" in events
        assert "complete" in events

        comp_chunk = next(c for c in chunks if c.event == "complete")
        assert "Overview" in comp_chunk.markdown
    finally:
        if temp_html.exists():
            temp_html.unlink()


@pytest.mark.anyio
async def test_run_pipeline_pdf_auto_detection():
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), "# PDF Report Title\n\nAutomated vision extraction test.")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        temp_pdf = Path(tf.name)

    doc.save(str(temp_pdf))
    doc.close()

    try:
        # Use PipelineType.AUTO to test auto-detection
        result = await run_pipeline(temp_pdf, pipeline_type=PipelineType.AUTO)
        assert result.success is True
        assert result.pipeline == PipelineType.VISION_OCR
        assert "PDF Report Title" in result.markdown
    finally:
        if temp_pdf.exists():
            temp_pdf.unlink()


@pytest.mark.anyio
async def test_stream_pipeline_voice_wav():
    # 0.5s silent WAV
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        temp_wav = Path(tf.name)

    with wave.open(str(temp_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(struct.pack("<h", 0) * 8000)

    try:
        chunks = []
        async for chunk in stream_pipeline(temp_wav, pipeline_type=PipelineType.AUTO):
            chunks.append(chunk)

        events = [c.event for c in chunks]
        assert "status" in events
        assert "complete" in events

        comp_chunk = next(c for c in chunks if c.event == "complete")
        assert "Audio Transcript" in comp_chunk.markdown
    finally:
        if temp_wav.exists():
            temp_wav.unlink()


@pytest.mark.anyio
async def test_runner_empty_file_error():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
        empty_txt = Path(tf.name)

    try:
        with pytest.raises(EmptyFileError):
            await run_pipeline(empty_txt, pipeline_type=PipelineType.TEXT_NORMALIZE)
    finally:
        if empty_txt.exists():
            empty_txt.unlink()
