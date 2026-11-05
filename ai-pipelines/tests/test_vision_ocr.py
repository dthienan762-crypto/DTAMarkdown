"""
Unit tests for Vision OCR Pipeline (/ai-pipelines/vision_ocr/)
Verifies PyMuPDF fast-path PDF extraction, GFM table formatting,
KaTeX equation repair, contrast checking, and boundary validation.
"""

import os
from pathlib import Path
import sys
import tempfile
import pytest
from PIL import Image

PIPELINES_DIR = Path(__file__).resolve().parent.parent
if str(PIPELINES_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINES_DIR))

from schemas import ConversionOptions, EmptyFileError, PipelineError, PipelineType
from vision_ocr.table_extractor import TableExtractor
from vision_ocr.math_extractor import MathExtractor
from vision_ocr.validator import PostProcessorValidator
from vision_ocr.ocr_engine import VisionOCREngine
import pymupdf


def test_table_extractor_grid_alignment():
    # Asymmetric input: row 1 has 3 cols, row 2 has 2 cols, row 3 has 1 col
    rows = [
        ["Header A", "Header B", "Header C"],
        ["Cell 1", "Cell 2 with | pipe"],
        ["Cell 3 with\nmulti-line"]
    ]
    gfm = TableExtractor.format_grid_to_gfm(rows)

    lines = [l.strip() for l in gfm.strip().split("\n")]
    assert len(lines) == 4  # Header, delimiter, 2 body rows

    # Verify column count in all rows is exactly 3
    import re
    for line in lines:
        cols = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
        assert len(cols) == 3

    # Verify escaped pipe and <br>
    assert r"Cell 2 with \| pipe" in gfm
    assert "Cell 3 with<br>multi-line" in gfm


def test_math_extractor_delimiters():
    raw = "Formula 1 is $ x + y = z $ and display is $$\nE = mc^2\n$$."
    cleaned = MathExtractor.clean_katex_delimiters(raw)

    assert "$x + y = z$" in cleaned
    assert "$$\nE = mc^2\n$$" in cleaned


def test_validator_repairs_unpaired_katex_and_tables():
    # Table with mismatched column counts
    broken = """
| Col 1 | Col 2 | Col 3 |
|---|---|---|
| Val 1 | Val 2 |
| Val 4 |

Here is an unclosed formula:
$$
x^2 + y^2 = 1
"""
    repaired, warnings = PostProcessorValidator.validate_and_repair(broken)

    # Table rows should be padded
    import re
    table_lines = [l for l in repaired.split("\n") if l.startswith("|")]
    for tl in table_lines:
        cols = [c.strip() for c in re.split(r"(?<!\\)\|", tl)[1:-1]]
        assert len(cols) == 3

    # Formula should be closed
    assert repaired.count("$$") % 2 == 0
    assert len(warnings) > 0


def test_vision_ocr_pdf_fast_path():
    # Create synthetic PDF in memory
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), "# Document Title\n\nThis is native digital vector text.")
    page.insert_text((50, 100), "Formula: $a^2 + b^2 = c^2$")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        temp_pdf = Path(tf.name)

    doc.save(str(temp_pdf))
    doc.close()

    try:
        engine = VisionOCREngine()
        options = ConversionOptions(extract_tables=True, extract_math=True, generate_toc=False)
        result = engine.convert(temp_pdf, options)

        assert result.success is True
        assert result.pipeline == PipelineType.VISION_OCR
        assert "Document Title" in result.markdown
        assert "$a^2 + b^2 = c^2$" in result.markdown
        assert result.metadata.get("engine_used") == "PyMuPDF Fast-Path"
    finally:
        if temp_pdf.exists():
            temp_pdf.unlink()


def test_vision_ocr_empty_and_corrupt_boundaries():
    engine = VisionOCREngine()
    options = ConversionOptions()

    # 1. 0-byte file boundary
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        empty_file = Path(tf.name)
    try:
        with pytest.raises(EmptyFileError):
            engine.convert(empty_file, options)
    finally:
        if empty_file.exists():
            empty_file.unlink()

    # 2. Corrupt file boundary
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        corrupt_file = Path(tf.name)
        corrupt_file.write_bytes(b"NOT_A_VALID_PNG_HEADER_RANDOM_GARBAGE")
    try:
        with pytest.raises(PipelineError):
            engine.convert(corrupt_file, options)
    finally:
        if corrupt_file.exists():
            corrupt_file.unlink()


def test_vision_ocr_low_contrast_image_detection():
    # Create flat low-contrast image
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
        low_contrast_path = Path(tf.name)

    img = Image.new("L", (100, 100), color=128)
    img.save(str(low_contrast_path))

    try:
        engine = VisionOCREngine()
        is_low, stddev = engine.check_image_contrast(low_contrast_path)
        assert is_low is True
        assert stddev < 1.0

        options = ConversionOptions(generate_toc=False, extract_tags=False)
        result = engine.convert(low_contrast_path, options)
        assert "[!WARNING] Low image contrast detected." in result.markdown
    finally:
        if low_contrast_path.exists():
            low_contrast_path.unlink()
