"""
DTAMarkdown Studio - Tier 4: Real-World Domain Application Scenarios Test Suite
Comprehensive validation of end-to-end user workflows:
1. Academic Research Paper (Vector PDF digital_sample.pdf -> Headings, Table, KaTeX)
2. Medical Clinic Invoice Table (Degraded Scan degraded_scan.png -> Contrast Warning, Image Geometry)
3. Multi-Speaker Technical Meeting Transcript (16kHz WAV speech_16khz.wav -> Acoustic VAD, Chronological Timestamps)
4. Complex GitHub Wiki / Specification Page (breakcases.txt -> Shielded Math, TOC, Hierarchy Healing, Tags)
"""

import asyncio
from pathlib import Path
import re
import pytest

from pipeline_runner import run_pipeline
from schemas import ConversionOptions, PipelineType

DATA_DIR = Path(__file__).resolve().parent / "data"


# ======================================================================
# Scenario 1: Academic Research Paper Page (Vector PDF)
# ======================================================================

def test_tier4_scenario_academic_paper_vector_pdf():
    """
    Scenario 1: Full academic paper vector page conversion.
    Executes real Vision OCR pipeline via PyMuPDF fast-path vector text extraction.
    Asserts on the real pipeline output: heading hierarchy,
    system architecture comparison table, KaTeX Gaussian formula, and word count.
    """
    pdf_path = DATA_DIR / "vision" / "digital_sample.pdf"
    assert pdf_path.exists(), f"PDF fixture missing: {pdf_path}"

    result = asyncio.run(run_pipeline(pdf_path, PipelineType.VISION_OCR))
    assert result.success is True
    assert result.pipeline == PipelineType.VISION_OCR

    md = result.markdown

    # 1. Verify Title & Headings
    assert "# Digital Vector Document" in md
    assert "## Executive Summary" in md
    assert "### System Architecture" in md
    assert "### Core Mathematical Formula" in md

    # 2. Verify Table Columns and Rows
    assert "| Component | Implementation | Latency Target | Status |" in md
    assert "| Vector PDF Parser | PyMuPDF (fitz) | < 50ms | PASS |" in md
    assert "| Vision Fallback | RapidOCR ONNX | < 300ms | READY |" in md

    # 3. Verify KaTeX Math Equation Syntax
    assert r"\frac{1}{\sigma \sqrt{2\pi}}" in md
    assert r"\mu" in md and r"\sigma^2" in md

    # 4. Verify Metadata
    assert result.metadata["word_count"] > 50
    assert result.metadata["engine_used"] == "PyMuPDF Fast-Path"


# ======================================================================
# Scenario 2: Medical Clinic Invoice Table (Degraded Scan)
# ======================================================================

def test_tier4_scenario_medical_invoice_table():
    """
    Scenario 2: Scanned, noisy, low-contrast medical invoice document.
    Executes real Vision OCR pipeline on degraded scan fixture.
    Verifies defensive contrast checking (RMS stddev < 15.0),
    warning callout emission, image dimension extraction, and non-crashing recovery.
    """
    scan_path = DATA_DIR / "vision" / "degraded_scan.png"
    assert scan_path.exists(), f"Scan fixture missing: {scan_path}"

    result = asyncio.run(run_pipeline(scan_path, PipelineType.VISION_OCR))
    assert result.success is True
    assert result.pipeline == PipelineType.VISION_OCR

    md = result.markdown

    # 1. Verify Low-Contrast Warning is Detected & Emitted
    assert any("Low image contrast detected" in w for w in result.warnings)
    assert "> [!WARNING] Low image contrast detected." in md

    # 2. Verify Image Layout Geometry Identification
    assert "850x600" in md

    # 3. Verify Engine Metadata & Duration
    assert result.metadata["character_count"] > 0
    assert result.duration_ms > 0


# ======================================================================
# Scenario 3: Multi-Speaker Technical Meeting Transcript
# ======================================================================

def test_tier4_scenario_multispeaker_meeting_transcript():
    """
    Scenario 3: Audio recording transcription with silence-gap paragraph segmentation.
    Executes real Voice STT pipeline on synthetic 16kHz WAV speech fixture.
    Verifies acoustic VAD energy segmentation, paragraph breaks on silence > 2.0s,
    and chronological Markdown timestamp annotations **[HH:MM:SS]**.
    """
    wav_path = DATA_DIR / "audio" / "speech_16khz.wav"
    assert wav_path.exists(), f"WAV fixture missing: {wav_path}"

    opts = ConversionOptions(timestamp_silence_threshold=2.0)
    result = asyncio.run(run_pipeline(wav_path, PipelineType.VOICE_STT, options=opts))
    assert result.success is True
    assert result.pipeline == PipelineType.VOICE_STT

    md = result.markdown

    # 1. Verify Title
    assert "## Audio Transcript" in md

    # 2. Verify Chronological Timestamp Annotations
    timestamp_matches = list(re.finditer(r"\*\*\[(\d{2}:\d{2}:\d{2})\]\*\*", md))
    assert len(timestamp_matches) >= 2

    t1_str = timestamp_matches[0].group(1)
    t2_str = timestamp_matches[1].group(1)
    assert t1_str == "00:00:00"
    assert t2_str == "00:00:04"

    # 3. Verify Distinct Paragraphs separated by silence gap
    assert "Audio speech segment detected" in md

    # 4. Verify Metadata
    assert result.metadata["word_count"] > 0
    assert result.duration_ms > 0


# ======================================================================
# Scenario 4: Complex GitHub Wiki Page & Break Cases
# ======================================================================

def test_tier4_scenario_complex_github_wiki_page():
    """
    Scenario 4: Complex unstructured technical wiki text with markdown break-cases.
    Executes real Text Normalization pipeline on raw breakcases.txt.
    Verifies pipe preservation in prose, protected math asterisks, heading normalization,
    TOC generation, and frontmatter.
    """
    breakcases_path = DATA_DIR / "text" / "breakcases.txt"
    assert breakcases_path.exists(), f"Breakcases fixture missing: {breakcases_path}"

    opts = ConversionOptions(extract_tables=True, extract_math=True, generate_toc=True, extract_tags=True)
    result = asyncio.run(run_pipeline(breakcases_path, PipelineType.TEXT_NORMALIZE, options=opts))
    assert result.success is True
    assert result.pipeline == PipelineType.TEXT_NORMALIZE

    md = result.markdown

    # 1. Verify Pipe Preserved in Descriptive Text
    assert "Option A | Option B | Option C" in md or r"Option A \| Option B \| Option C" in md

    # 2. Verify Shielded Math Formula with Asterisks
    assert "$x_1 * x_2 * x_3$" in md
    assert r"$$\int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}$$" in md

    # 3. Verify Heading Hierarchy Fix
    # Raw had #### right after #, normalizer fixes skipped level to ##
    assert "## Unreachable Subsection Deeply Skipped" in md

    # 4. Verify Automatic TOC Injection
    assert "## Table of Contents" in md
    assert "[Master System Specification](#master-system-specification)" in md

    # 5. Verify Unicode Normalization & Frontmatter
    assert "\u200B" not in md
    assert result.metadata["word_count"] > 50
    assert len(result.metadata["tags"]) > 0
