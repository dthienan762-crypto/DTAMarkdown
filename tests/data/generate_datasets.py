#!/usr/bin/env python3
"""
DTAMarkdown Studio - Synthetic Test Datasets Generator
Pure-Python generator for multimodal test fixtures:
- tests/data/vision/: clean_table_math.png, degraded_scan.png, digital_sample.pdf, empty_0byte.png
- tests/data/audio/: speech_16khz.wav, empty_audio.wav, corrupt_audio.wav
- tests/data/text/: messy_tables.html, breakcases.txt
- tests/data/expected/: Golden baseline expected Markdown files
"""

from pathlib import Path
import math
import random
import struct
import sys
import wave

# Reconfigure stdout for UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import pymupdf


BASE_DIR = Path(__file__).resolve().parent
VISION_DIR = BASE_DIR / "vision"
AUDIO_DIR = BASE_DIR / "audio"
TEXT_DIR = BASE_DIR / "text"
EXPECTED_DIR = BASE_DIR / "expected"


def ensure_directories():
    for d in [VISION_DIR, AUDIO_DIR, TEXT_DIR, EXPECTED_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def generate_clean_table_math():
    """Generates a high-contrast clean image with a table and KaTeX formula."""
    img = Image.new("RGB", (900, 650), color="white")
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((40, 30), "Quarterly Performance & Metric Analysis", fill="black")

    # Table Grid
    table_x, table_y = 40, 80
    cell_w, cell_h = 180, 45
    rows = [
        ["Quarter", "Revenue", "Gross Margin", "Net Income"],
        ["Q1-2026", "$1,250,000", "42.5%", "$310,000"],
        ["Q2-2026", "$1,480,000", "44.0%", "$395,000"],
        ["Q3-2026", "$1,620,000", "45.2%", "$440,000"],
        ["Q4-2026", "$1,910,000", "46.8%", "$530,000"],
    ]

    for r_idx, row in enumerate(rows):
        y = table_y + r_idx * cell_h
        for c_idx, val in enumerate(row):
            x = table_x + c_idx * cell_w
            # Draw cell box
            draw.rectangle([x, y, x + cell_w, y + cell_h], outline="black", width=2 if r_idx == 0 else 1)
            # Header background
            if r_idx == 0:
                draw.rectangle([x + 1, y + 1, x + cell_w - 1, y + cell_h - 1], fill="#EAEAEA")
            draw.text((x + 15, y + 15), val, fill="black")

    # Mathematical Equations
    math_y = table_y + len(rows) * cell_h + 50
    draw.text((40, math_y), "Theoretical Profit Optimization Model:", fill="black")
    draw.text((60, math_y + 35), "Inline constraint: f(x) = x^2 - 4x + 7 >= 0", fill="#111827")
    draw.text((60, math_y + 75), "Quadratic Solution Formula:", fill="black")
    draw.text((80, math_y + 110), "x = (-b +- sqrt(b^2 - 4ac)) / (2a)", fill="#1E3A8A")
    draw.text((80, math_y + 150), "LaTeX equivalent: $$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$", fill="#374151")

    out_path = VISION_DIR / "clean_table_math.png"
    img.save(out_path, format="PNG")
    print(f"Generated: {out_path} ({out_path.stat().st_size} bytes)")


def generate_degraded_scan():
    """Generates a degraded, noisy, slightly rotated scanned table invoice."""
    img = Image.new("RGB", (850, 600), color="#F9F9F6")
    draw = ImageDraw.Draw(img)

    # Draw low-contrast header
    draw.text((50, 40), "MEDICAL CLINIC INVOICE & LAB CHARGES", fill="#333333")

    # Table coordinates
    tx, ty = 50, 90
    col_widths = [160, 220, 140, 160]
    data = [
        ["Procedure Code", "Description", "Units", "Amount"],
        ["CPT-99214", "Office Visit Level 4", "1", "$175.00"],
        ["CPT-80053", "Comprehensive Metabolic Panel", "1", "$62.50"],
        ["CPT-85025", "Complete Blood Count (CBC)", "2", "$44.00"],
        ["TOTAL", "Total Patient Responsibility", "--", "$281.50"],
    ]

    for r_idx, row in enumerate(data):
        y = ty + r_idx * 40
        curr_x = tx
        for c_idx, text in enumerate(row):
            w = col_widths[c_idx]
            draw.rectangle([curr_x, y, curr_x + w, y + 40], outline="#666666", width=1)
            draw.text((curr_x + 10, y + 12), text, fill="#222222")
            curr_x += w

    # Add degraded scanned formula
    draw.text((50, 320), "Dosage adjustment factor: D_adj = D_0 * (BSA / 1.73)", fill="#444444")
    draw.text((50, 360), "LaTeX: $$D_{adj} = D_0 \\cdot \\frac{BSA}{1.73}$$", fill="#444444")

    # Add Gaussian-like noise & grain
    pixels = img.load()
    w, h = img.size
    for _ in range(12000):
        rx = random.randint(0, w - 1)
        ry = random.randint(0, h - 1)
        noise_val = random.randint(180, 230)
        pixels[rx, ry] = (noise_val, noise_val, noise_val)

    # Slight rotation to simulate tilted scanner (1.5 degrees)
    img_rotated = img.rotate(1.5, resample=Image.Resampling.BILINEAR, fillcolor="#F0F0F0")

    # Slight blur to simulate scanner defocus
    img_blurred = img_rotated.filter(ImageFilter.GaussianBlur(radius=0.7))

    out_path = VISION_DIR / "degraded_scan.png"
    img_blurred.save(out_path, format="PNG")
    print(f"Generated: {out_path} ({out_path.stat().st_size} bytes)")


def generate_digital_sample_pdf():
    """Generates a pure vector PDF sample with selectable text, headings, and table."""
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # Standard A4 size

    text_content = """# Digital Vector Document

## Executive Summary
This document serves as the ground truth benchmark for PyMuPDF digital vector text and table extraction. It operates with zero OCR overhead and sub-50ms latency.

### System Architecture
| Component | Implementation | Latency Target | Status |
|---|---|---|---|
| Vector PDF Parser | PyMuPDF (fitz) | < 50ms | PASS |
| Vision Fallback | RapidOCR ONNX | < 300ms | READY |
| Cloud Vision API | Gemini Multimodal | < 1200ms | READY |

### Core Mathematical Formula
The Gaussian normal probability density function is defined as:

$$f(x) = \\frac{1}{\\sigma \\sqrt{2\\pi}} e^{-\\frac{1}{2}\\left(\\frac{x-\\mu}{\\sigma}\\right)^2}$$

Where $\\mu$ is the mean and $\\sigma^2$ is the variance.
"""
    # Write text to PDF page
    rect = pymupdf.Rect(40, 50, 555, 792)
    page.insert_textbox(rect, text_content, fontsize=11, fontname="helv", color=(0.1, 0.1, 0.1))

    out_path = VISION_DIR / "digital_sample.pdf"
    doc.save(out_path)
    doc.close()
    print(f"Generated: {out_path} ({out_path.stat().st_size} bytes)")


def generate_empty_0byte():
    """Generates a 0-byte file to test defensive empty payload boundaries."""
    out_path = VISION_DIR / "empty_0byte.png"
    out_path.write_bytes(b"")
    print(f"Generated: {out_path} ({out_path.stat().st_size} bytes)")


def generate_speech_16khz_wav():
    """
    Generates a synthetic 16kHz mono 16-bit PCM WAV file.
    Includes:
    - Tone burst 1 (1.5 seconds) simulating speech phrase 1
    - Silence gap (2.5 seconds > 2.0s silence threshold)
    - Tone burst 2 (1.5 seconds) simulating speech phrase 2
    Total duration: 5.5 seconds
    """
    sample_rate = 16000
    out_path = AUDIO_DIR / "speech_16khz.wav"

    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit PCM (2 bytes)
        wf.setframerate(sample_rate)

        frames = bytearray()

        def add_tone_phrase(duration_sec, base_freq):
            num_samples = int(sample_rate * duration_sec)
            for i in range(num_samples):
                t = float(i) / sample_rate
                # Formant simulation with modulated sine waves
                val = 0.5 * math.sin(2 * math.pi * base_freq * t) + \
                      0.3 * math.sin(2 * math.pi * (base_freq * 2.1) * t) + \
                      0.15 * math.sin(2 * math.pi * (base_freq * 3.2) * t)
                # Envelope attack and decay
                envelope = math.sin(math.pi * (i / num_samples))
                sample_int = int(val * envelope * 22000.0)
                sample_int = max(-32768, min(32767, sample_int))
                frames.extend(struct.pack("<h", sample_int))

        def add_silence(duration_sec):
            num_samples = int(sample_rate * duration_sec)
            frames.extend(b"\x00\x00" * num_samples)

        # 1. First phrase (1.5s)
        add_tone_phrase(1.5, 240.0)
        # 2. Silence gap (2.5s) -> triggers new paragraph boundary (>2.0s)
        add_silence(2.5)
        # 3. Second phrase (1.5s)
        add_tone_phrase(1.5, 310.0)

        wf.writeframes(frames)

    print(f"Generated: {out_path} ({out_path.stat().st_size} bytes, 5.5s @ 16kHz)")


def generate_audio_boundaries():
    """Generates 0-byte audio and corrupted audio byte files."""
    # 0-byte audio file
    empty_path = AUDIO_DIR / "empty_audio.wav"
    empty_path.write_bytes(b"")
    print(f"Generated: {empty_path} ({empty_path.stat().st_size} bytes)")

    # Corrupt audio bytes (non-WAV header and garbage data)
    corrupt_path = AUDIO_DIR / "corrupt_audio.wav"
    corrupt_data = b"RIFF\xff\xff\xff\xffNOTWAVE_GARBAGE_BINARY_STREAM_0123456789\xde\xad\xbe\xef" * 16
    corrupt_path.write_bytes(corrupt_data)
    print(f"Generated: {corrupt_path} ({corrupt_path.stat().st_size} bytes)")


def generate_messy_tables_html():
    """Generates malformed HTML with unclosed tags, colspan, nested tables, and math."""
    html_content = """<!DOCTYPE html>
<html>
<head><title>Messy Enterprise Report</title></head>
<body>
  <h1>Quarterly Financial Review</h1>
  <p>Overview of departmental revenues with math invariant $R_{total} = \\sum_{i=1}^{k} R_i$ and unescaped ampersands: AT&T & Johnson & Johnson.</p>
  
  <!-- Broken Table 1: Missing closing tags and mismatched cells -->
  <table>
    <tr><th>Department<th>Budget<th>Actual Expenditure
    <tr><td>Engineering<td>$850,000<td>$812,000
    <tr><td colspan="2">Operations & Infrastructure Combined<td>$640,000
    <tr><td>Marketing<td>$420,000<td>$445,000
  </table>

  <div>
    <h2>Nested Legacy Table Structure</h2>
    <!-- Nested Table: outer table contains inner table inside a cell -->
    <table border="1">
      <tr>
        <td>Outer Section 1</td>
        <td>
          <table class="inner">
            <tr><th>Metric</th><th>Score</th></tr>
            <tr><td>Uptime</td><td>99.98%</td></tr>
            <tr><td>Error Rate</td><td>0.02%</td></tr>
          </table>
        </td>
      </tr>
      <tr>
        <td>Outer Section 2</td>
        <td>All secondary services operational.</td>
      </tr>
    </table>
  </div>
</body>
</html>
"""
    out_path = TEXT_DIR / "messy_tables.html"
    out_path.write_text(html_content, encoding="utf-8")
    print(f"Generated: {out_path} ({out_path.stat().st_size} bytes)")


def generate_breakcases_txt():
    """Generates raw text with markdown edge cases, unescaped pipes, skipped headers, and shielded math."""
    text_content = """# Master System Specification

#### Unreachable Subsection Deeply Skipped

The pipeline must handle unescaped pipe | characters within descriptive sentences without breaking GFM column alignment.
For example: Option A | Option B | Option C are valid choices.

Mathematical collision scenario:
$x_1 * x_2 * x_3$ represents a three-way interaction variable.
Notice the asterisks * should not trigger italic formatting inside LaTeX.

Another formula:
$$\\int_{0}^{\\infty} e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}$$

Unclosed math delimiter edge case:
This line contains a dangling $single dollar sign that is not closed.

Unicode anomalies:
Invisible zero-width space here: [\u200B]
Non-breaking space here: [\u00A0]
Smart quotes: \u201cDTAMarkdown Studio\u201d and em-dash \u2014 robust parser.
"""
    out_path = TEXT_DIR / "breakcases.txt"
    out_path.write_text(text_content, encoding="utf-8")
    print(f"Generated: {out_path} ({out_path.stat().st_size} bytes)")


def generate_expected_goldens():
    """Generates golden baseline expected Markdown files for regression testing."""
    # 1. Clean table + math expected
    clean_expected = """# Quarterly Performance & Metric Analysis

| Quarter | Revenue | Gross Margin | Net Income |
|---|---|---|---|
| Q1-2026 | $1,250,000 | 42.5% | $310,000 |
| Q2-2026 | $1,480,000 | 44.0% | $395,000 |
| Q3-2026 | $1,620,000 | 45.2% | $440,000 |
| Q4-2026 | $1,910,000 | 46.8% | $530,000 |

Theoretical Profit Optimization Model:
Inline constraint: $f(x) = x^2 - 4x + 7 \\ge 0$

Quadratic Solution Formula:
$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$
"""
    (EXPECTED_DIR / "clean_table_math.expected.md").write_text(clean_expected, encoding="utf-8")

    # 2. Degraded scan expected
    degraded_expected = """# MEDICAL CLINIC INVOICE & LAB CHARGES

| Procedure Code | Description | Units | Amount |
|---|---|---|---|
| CPT-99214 | Office Visit Level 4 | 1 | $175.00 |
| CPT-80053 | Comprehensive Metabolic Panel | 1 | $62.50 |
| CPT-85025 | Complete Blood Count (CBC) | 2 | $44.00 |
| TOTAL | Total Patient Responsibility | -- | $281.50 |

Dosage adjustment factor:
$$D_{adj} = D_0 \\cdot \\frac{BSA}{1.73}$$
"""
    (EXPECTED_DIR / "degraded_scan.expected.md").write_text(degraded_expected, encoding="utf-8")

    # 3. Digital PDF sample expected
    pdf_expected = """# Digital Vector Document

## Executive Summary
This document serves as the ground truth benchmark for PyMuPDF digital vector text and table extraction. It operates with zero OCR overhead and sub-50ms latency.

### System Architecture
| Component | Implementation | Latency Target | Status |
|---|---|---|---|
| Vector PDF Parser | PyMuPDF (fitz) | < 50ms | PASS |
| Vision Fallback | RapidOCR ONNX | < 300ms | READY |
| Cloud Vision API | Gemini Multimodal | < 1200ms | READY |

### Core Mathematical Formula
The Gaussian normal probability density function is defined as:

$$f(x) = \\frac{1}{\\sigma \\sqrt{2\\pi}} e^{-\\frac{1}{2}\\left(\\frac{x-\\mu}{\\sigma}\\right)^2}$$

Where $\\mu$ is the mean and $\\sigma^2$ is the variance.
"""
    (EXPECTED_DIR / "digital_sample.expected.md").write_text(pdf_expected, encoding="utf-8")

    # 4. Messy tables HTML expected
    html_expected = r"""# Quarterly Financial Review

Overview of departmental revenues with math invariant $R_{total} = \sum_{i=1}^{k} R_i$ and unescaped ampersands: AT&T & Johnson & Johnson.

| Department | Budget | Actual Expenditure |
|---|---|---|
| Engineering | $850,000 | $812,000 |
| Operations & Infrastructure Combined | Operations & Infrastructure Combined | $640,000 |
| Marketing | $420,000 | $445,000 |

## Nested Legacy Table Structure

| Section | Details |
|---|---|
| Outer Section 1 | Uptime: 99.98% \| Error Rate: 0.02% |
| Outer Section 2 | All secondary services operational. |
"""
    (EXPECTED_DIR / "messy_tables.expected.md").write_text(html_expected, encoding="utf-8")

    # 5. Breakcases expected
    breakcases_expected = """# Master System Specification

## Unreachable Subsection Deeply Skipped

The pipeline must handle unescaped pipe \\| characters within descriptive sentences without breaking GFM column alignment.
For example: Option A \\| Option B \\| Option C are valid choices.

Mathematical collision scenario:
$x_1 * x_2 * x_3$ represents a three-way interaction variable.
Notice the asterisks * should not trigger italic formatting inside LaTeX.

Another formula:
$$\\int_{0}^{\\infty} e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}$$

Unclosed math delimiter edge case:
This line contains a dangling $single dollar sign that is not closed.

Unicode anomalies:
Invisible zero-width space here: []
Non-breaking space here: [ ]
Smart quotes: "DTAMarkdown Studio" and em-dash — robust parser.
"""
    (EXPECTED_DIR / "breakcases.expected.md").write_text(breakcases_expected, encoding="utf-8")

    # 6. Audio transcript expected with timestamped paragraphs
    audio_expected = """## Audio Transcript

**[00:00:00]** Synthetic test audio phrase 1 generated at 16kHz.

**[00:00:04]** Synthetic test audio phrase 2 resumed after silence interval.
"""
    (EXPECTED_DIR / "speech_16khz.expected.md").write_text(audio_expected, encoding="utf-8")

    print(f"Generated 6 golden expected Markdown files in {EXPECTED_DIR}")


def main():
    print("=== DTAMarkdown Studio: Generating Synthetic Test Datasets ===")
    ensure_directories()
    generate_clean_table_math()
    generate_degraded_scan()
    generate_digital_sample_pdf()
    generate_empty_0byte()
    generate_speech_16khz_wav()
    generate_audio_boundaries()
    generate_messy_tables_html()
    generate_breakcases_txt()
    generate_expected_goldens()
    print("=== All Synthetic Datasets Successfully Generated ===")


if __name__ == "__main__":
    main()
