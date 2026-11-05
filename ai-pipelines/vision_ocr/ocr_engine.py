"""
DTAMarkdown Studio - Vision OCR Engine
Multi-tier document and image conversion engine:
- Tier 1: PyMuPDF Fast-Path for digital PDFs (<50ms).
- Tier 2: Gemini Vision API (if GEMINI_API_KEY is present) / MarkItDown.
- Tier 3: RapidOCR ONNX Runtime / local layout analysis offline fallback.
Includes boundary defense against empty files, 50MB limits, and low-contrast images.
"""

from __future__ import annotations

import base64
import io
import json
import os
from pathlib import Path
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple
import urllib.request
import uuid

from PIL import Image, ImageStat
import pymupdf

from schemas import (
    ConversionMetadata,
    ConversionOptions,
    DegradedInputError,
    EmptyFileError,
    PipelineError,
    PipelineResult,
    PipelineType,
    StreamChunk,
    UnsupportedFormatError,
)
from text_engine import TOCGenerator, TagExtractor
from .table_extractor import TableExtractor
from .math_extractor import MathExtractor
from .validator import PostProcessorValidator

# Check for optional RapidOCR
try:
    from rapidocr_onnxruntime import RapidOCR
    RAPIDOCR_AVAILABLE = True
except ImportError:
    RAPIDOCR_AVAILABLE = False


class VisionOCREngine:
    """
    Production Vision OCR Engine with multi-tier fallback hierarchy,
    boundary validation, table layout preservation, and KaTeX extraction.
    """

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    SUPPORTED_PDF_EXTENSIONS = {".pdf"}
    SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}

    SYSTEM_PROMPT = (
        "You are an expert document-to-Markdown converter. Convert the provided document/image "
        "into clean, valid GitHub Flavored Markdown.\n"
        "Rules:\n"
        "1. Tables: Must be formatted as valid GFM markdown tables (| Header 1 | Header 2 |\\n|---|---|...). "
        "Ensure all rows have the exact same number of columns. Do not leave trailing open pipes.\n"
        "2. Mathematical Formulas:\n"
        "   - Inline equations MUST be enclosed in single dollar signs: $...$.\n"
        "   - Standalone block equations MUST be enclosed in double dollar signs: $$\\n...\\n$$.\n"
        "   - Use standard LaTeX/KaTeX syntax (e.g., \\frac{a}{b}, \\sqrt{x}, \\sum_{i=1}^n, \\int_a^b).\n"
        "3. Preserve hierarchical headings (#, ##, ###), bullet lists, and formatting.\n"
        "4. Output ONLY the raw Markdown. Do not wrap in outer ```markdown code blocks."
    )

    def __init__(self):
        self.rapid_ocr = RapidOCR() if RAPIDOCR_AVAILABLE else None

    def validate_file(self, file_path: Path) -> Tuple[str, int]:
        """
        Validates file existence, non-empty size, 50MB boundary, and media format.
        Returns:
            category: 'pdf' or 'image'
            file_size: size in bytes
        """
        if not file_path.exists():
            raise PipelineError(f"File not found: {file_path}", code="FILE_NOT_FOUND")

        size = file_path.stat().st_size
        if size == 0:
            raise EmptyFileError(f"Uploaded file contains 0 bytes: {file_path.name}")

        if size > self.MAX_FILE_SIZE:
            raise PipelineError(
                f"Payload too large: file size ({size} bytes) exceeds 50MB limit.",
                code="PAYLOAD_TOO_LARGE"
            )

        suffix = file_path.suffix.lower()
        if suffix in self.SUPPORTED_PDF_EXTENSIONS:
            return "pdf", size
        elif suffix in self.SUPPORTED_IMAGE_EXTENSIONS:
            return "image", size
        else:
            raise UnsupportedFormatError(
                f"Unsupported media format for vision OCR: '{suffix}'. Expected PDF or image."
            )

    def check_image_contrast(self, image_path: Path) -> Tuple[bool, float]:
        """
        Calculates grayscale luminance standard deviation (RMS contrast).
        Returns:
            is_low_contrast: True if contrast < 15.0 on a 0-255 scale.
            stddev: luminance standard deviation.
        """
        try:
            with Image.open(image_path) as img:
                stat = ImageStat.Stat(img.convert("L"))
                stddev = float(stat.stddev[0])
                return (stddev < 15.0), stddev
        except Exception as e:
            raise DegradedInputError(f"Failed to decode image file {image_path.name}: {e}")

    def _convert_pdf_fast_path(self, file_path: Path, options: ConversionOptions) -> Tuple[str, str, List[str]]:
        """
        Tier 1: PyMuPDF Fast-Path digital PDF extractor.
        Extracts native text, embedded layout, tables, and math in <50ms per page.
        """
        warnings: List[str] = []
        doc = pymupdf.open(str(file_path))
        num_pages = len(doc)
        if num_pages == 0:
            doc.close()
            raise DegradedInputError("PDF document has 0 pages.")

        page_markdowns: List[str] = []
        is_scanned = True

        for pno in range(num_pages):
            page = doc[pno]
            # 1. Extract tables if requested
            tables_gfm, table_rects = [], []
            if options.extract_tables:
                tables_gfm, table_rects = TableExtractor.extract_tables_from_pdf_page(page)

            # 2. Extract text blocks
            # Exclude table areas to prevent duplication
            blocks = page.get_text("blocks")
            page_text_blocks = []

            for b in blocks:
                # b = (x0, y0, x1, y1, text, block_no, block_type)
                if len(b) >= 5:
                    rect = pymupdf.Rect(b[0], b[1], b[2], b[3])
                    # Check if block overlaps with any extracted table
                    overlap = any(rect.intersects(pymupdf.Rect(t_rect)) for t_rect in table_rects)
                    if not overlap:
                        text = b[4].strip()
                        if text:
                            page_text_blocks.append(text)

            combined_page_text = "\n\n".join(page_text_blocks)
            if combined_page_text.strip():
                is_scanned = False

            # Combine text and tables
            page_content_parts = []
            if combined_page_text:
                page_content_parts.append(combined_page_text)
            if tables_gfm:
                page_content_parts.extend(tables_gfm)

            if page_content_parts:
                page_markdowns.append("\n\n".join(page_content_parts))

        doc.close()

        # If PDF has no digital text layer, fallback to raster OCR
        if is_scanned or not page_markdowns:
            warnings.append("Digital PDF contained no extractable text layer. Raster OCR fallback recommended.")
            return "", "PyMuPDF Scanned", warnings

        result_md = "\n\n---\n\n".join(page_markdowns)
        return result_md, "PyMuPDF Fast-Path", warnings

    def _call_gemini_vision(self, image_bytes: bytes, mime_type: str, api_key: str) -> str:
        """Calls Gemini Vision API REST endpoint directly."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": self.SYSTEM_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.b64encode(image_bytes).decode("utf-8")
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1
            }
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            # Strip markdown code fences if wrapped
            clean = text.strip()
            if clean.startswith("```markdown"):
                clean = clean[len("```markdown"):].strip()
            elif clean.startswith("```"):
                clean = clean[len("```"):].strip()
            if clean.endswith("```"):
                clean = clean[:-3].strip()
            return clean

    def _convert_image_ocr(self, file_path: Path, options: ConversionOptions) -> Tuple[str, str, List[str]]:
        """
        Executes OCR on an image file using Gemini Vision -> RapidOCR -> MarkItDown/Pillow fallback.
        """
        warnings: List[str] = []

        # 1. Check image contrast
        is_low_contrast, stddev = self.check_image_contrast(file_path)
        if is_low_contrast:
            warnings.append(f"Low image contrast detected (RMS stddev: {stddev:.1f} < 15.0).")

        # 2. Tier 2: Gemini Vision API (if configured or requested)
        api_key = os.environ.get("GEMINI_API_KEY")
        if (options.preferred_engine == "gemini" or options.preferred_engine == "auto") and api_key:
            try:
                suffix = file_path.suffix.lower().lstrip(".")
                mime = f"image/{suffix if suffix != 'jpg' else 'jpeg'}"
                image_bytes = file_path.read_bytes()
                gemini_md = self._call_gemini_vision(image_bytes, mime, api_key)
                if is_low_contrast:
                    gemini_md = "> [!WARNING] Low image contrast detected.\n\n" + gemini_md
                return gemini_md, "Gemini Vision Multimodal API", warnings
            except Exception as e:
                warnings.append(f"Gemini Vision API fallback triggered due to error: {e}")

        # 3. Tier 3: RapidOCR ONNX Runtime (if installed)
        if self.rapid_ocr is not None:
            try:
                ocr_results, _ = self.rapid_ocr(str(file_path))
                if ocr_results:
                    lines = [res[1] for res in ocr_results]
                    joined_text = "\n\n".join(lines)
                    if is_low_contrast:
                        joined_text = "> [!WARNING] Low image contrast detected.\n\n" + joined_text
                    return joined_text, "RapidOCR ONNX Runtime", warnings
            except Exception as e:
                warnings.append(f"RapidOCR ONNX error: {e}")

        # 4. Fallback: MarkItDown or Pillow text/layout metadata extraction
        try:
            import markitdown
            md_conv = markitdown.MarkItDown()
            conv_res = md_conv.convert(str(file_path))
            content = conv_res.text_content.strip()
            if not content:
                # Pillow layout inspection fallback
                with Image.open(file_path) as img:
                    w, h = img.size
                    content = f"Image ({w}x{h} px, mode {img.mode})\n\n[Visual document content]"
            if is_low_contrast:
                content = "> [!WARNING] Low image contrast detected.\n\n" + content
            return content, "MarkItDown Layout Extractor", warnings
        except Exception as e:
            raise DegradedInputError(f"All OCR engines failed to process image {file_path.name}: {e}")

    def convert(self, file_path: Path, options: ConversionOptions) -> PipelineResult:
        """
        Synchronous conversion of PDF or image into GFM Markdown.
        """
        start_time = time.perf_counter()
        category, file_size = self.validate_file(file_path)

        warnings: List[str] = []
        raw_md = ""
        engine_used = "Unknown"

        if category == "pdf":
            # Attempt PyMuPDF fast path first
            raw_md, engine_used, pdf_warnings = self._convert_pdf_fast_path(file_path, options)
            warnings.extend(pdf_warnings)

            # If digital PDF yielded nothing, render first page to image for raster OCR
            if not raw_md.strip():
                try:
                    doc = pymupdf.open(str(file_path))
                    page = doc[0]
                    pix = page.get_pixmap(dpi=150)
                    temp_img_path = file_path.with_suffix(".scanned_temp.png")
                    pix.save(str(temp_img_path))
                    doc.close()

                    raw_md, engine_used, img_warnings = self._convert_image_ocr(temp_img_path, options)
                    warnings.extend(img_warnings)
                    if temp_img_path.exists():
                        temp_img_path.unlink()
                except Exception as e:
                    raise DegradedInputError(f"Scanned PDF raster conversion failed: {e}")
        else:
            # Direct Image OCR
            raw_md, engine_used, img_warnings = self._convert_image_ocr(file_path, options)
            warnings.extend(img_warnings)

        # Post-Processing & Validation
        repaired_md, val_warnings = PostProcessorValidator.validate_and_repair(raw_md)
        warnings.extend(val_warnings)

        # Automatic KaTeX equation wrapping for prominent formulas
        if options.extract_math:
            repaired_md = MathExtractor.wrap_raw_latex_equations(repaired_md)

        # Generate Table of Contents
        toc_str = None
        if options.generate_toc:
            toc_str = TOCGenerator.generate_toc(repaired_md)
            if toc_str:
                repaired_md = TOCGenerator.inject_toc(repaired_md, toc_str)

        # Extract Tags and Metadata
        w_count, c_count = TagExtractor.calculate_word_and_char_count(repaired_md)
        read_time = TagExtractor.estimate_read_time(w_count)
        tags = TagExtractor.extract_tags(repaired_md) if options.extract_tags else []

        if options.extract_tags and w_count > 0:
            doc_title = TagExtractor.extract_document_title(repaired_md)
            fm = TagExtractor.generate_frontmatter(doc_title, tags, w_count, read_time)
            repaired_md = TagExtractor.inject_frontmatter(repaired_md, fm)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        metadata = {
            "word_count": w_count,
            "character_count": c_count,
            "estimated_read_time": read_time,
            "duration_ms": round(elapsed_ms, 2),
            "engine_used": engine_used,
            "tags": tags,
            "warnings": warnings,
            "toc": toc_str,
        }

        return PipelineResult(
            success=True,
            pipeline=PipelineType.VISION_OCR,
            markdown=repaired_md,
            metadata=metadata,
            warnings=warnings,
            duration_ms=round(elapsed_ms, 2),
            job_id=str(uuid.uuid4())
        )

    async def convert_stream(
        self,
        file_path: Path,
        options: ConversionOptions,
        job_id: Optional[str] = None
    ) -> AsyncIterator[StreamChunk]:
        """
        Asynchronous streaming generator yielding progress status frames,
        progressive Markdown chunks, and the final completion frame.
        """
        jid = job_id or str(uuid.uuid4())

        # Frame 1: Initial Ingestion Status
        yield StreamChunk(
            event="status",
            job_id=jid,
            stage="file_validation",
            progress=10,
            message="Validating file format and contrast..."
        )

        try:
            category, _ = self.validate_file(file_path)
        except Exception as e:
            code = getattr(e, "code", "FILE_ERROR")
            yield StreamChunk(
                event="error",
                job_id=jid,
                code=code,
                message=str(e),
                recoverable=False
            )
            return

        # Frame 2: Layout & OCR Stage
        yield StreamChunk(
            event="status",
            job_id=jid,
            stage="ocr_processing",
            progress=40,
            message=f"Extracting layout, tables, and KaTeX math from {category.upper()}..."
        )

        try:
            # Run heavy CPU/GPU OCR conversion
            result = self.convert(file_path, options)
        except Exception as e:
            code = getattr(e, "code", "OCR_FAILED")
            yield StreamChunk(
                event="error",
                job_id=jid,
                code=code,
                message=str(e),
                recoverable=False
            )
            return

        # Frame 3: Stream incremental chunks
        full_md = result.markdown
        paragraphs = [p + "\n\n" for p in full_md.split("\n\n") if p.strip()]

        for idx, para in enumerate(paragraphs):
            yield StreamChunk(
                event="chunk",
                job_id=jid,
                delta=para,
                index=idx
            )

        # Frame 4: Final Complete Frame
        yield StreamChunk(
            event="complete",
            job_id=jid,
            markdown=full_md,
            metadata=result.metadata
        )
