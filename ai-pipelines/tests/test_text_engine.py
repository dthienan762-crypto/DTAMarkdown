"""
Unit tests for Text Normalization Engine (/ai-pipelines/text_engine/)
Verifies HTML sanitization, table normalization (colspan/rowspan, nested tables, pipes),
MathShield preservation, TOC generation, and Tag/Metadata extraction.
"""

import sys
from pathlib import Path
import pytest

# Add ai-pipelines to path
PIPELINES_DIR = Path(__file__).resolve().parent.parent
if str(PIPELINES_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINES_DIR))

from text_engine.math_shield import MathShield
from text_engine.normalizer import TableNormalizer, TextNormalizer
from text_engine.toc_generator import TOCGenerator, generate_github_slug
from text_engine.tag_extractor import TagExtractor


def test_math_shield_inline_and_display():
    ms = MathShield()
    sample = "We have inline $E = mc^2$ and display:\n$$\nx = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}\n$$\nDone."
    shielded, tokens = ms.shield(sample)

    assert len(tokens) == 2
    # Verify display is first
    assert tokens[0][2] is True
    assert "\\frac" in tokens[0][1]
    # Verify inline is second
    assert tokens[1][2] is False
    assert "$E = mc^2$" == tokens[1][1]

    # Verify shielded text does not contain LaTeX symbols
    assert "\\frac" not in shielded
    assert "$E = mc^2$" not in shielded

    # Unshield
    restored = ms.unshield(shielded, tokens)
    assert restored == sample


def test_math_shield_currency_not_matched():
    ms = MathShield()
    sample = "The cost is $20 and discount is $5.50 or $1,000."
    shielded, tokens = ms.shield(sample)
    assert len(tokens) == 0
    assert shielded == sample


def test_table_normalizer_nested_and_colspan():
    html = """
    <table border="1">
      <tr>
        <th colspan="2">Merged Header</th>
        <th>Single Header</th>
      </tr>
      <tr>
        <td>Val A</td>
        <td>Val B with | pipe</td>
        <td>
          <table>
            <tr><td>Inner 1</td><td>Inner 2</td></tr>
          </table>
        </td>
      </tr>
      <tr>
        <td rowspan="2">Span Row</td>
        <td>Row 2 Col 2</td>
        <td>Row 2 Col 3</td>
      </tr>
      <tr>
        <td>Row 3 Col 2</td>
        <td>Row 3 Col 3</td>
      </tr>
    </table>
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    gfm = TableNormalizer.html_table_to_gfm(table)

    lines = [line.strip() for line in gfm.strip().split("\n")]
    assert len(lines) >= 4  # Header, delimiter, and rows

    # Check header has 3 columns
    header_cols = [c.strip() for c in lines[0].split("|")[1:-1]]
    assert len(header_cols) == 3
    assert header_cols[0] == "Merged Header"

    # Check delimiter has 3 columns
    delims = [c.strip() for c in lines[1].split("|")[1:-1]]
    assert len(delims) == 3
    assert all(d == "---" for d in delims)

    # Check all rows have exactly 3 columns using unescaped pipe regex
    import re
    for row_line in lines[2:]:
        # Split by unescaped pipe |
        cols = [c.strip() for c in re.split(r"(?<!\\)\|", row_line)[1:-1]]
        assert len(cols) == 3

    # Check escaped pipe
    assert r"Val B with \| pipe" in gfm


def test_text_normalizer_full_pipeline():
    tn = TextNormalizer()
    raw = """
    <html>
      <head><script>alert('xss')</script></head>
      <body>
        <h1 onclick="malicious()">Document Title</h1>
        <p>Formula: $x_1 * x_2 = y$ and price $100.</p>
        <p>Display:
        $$
        \\sum_{i=1}^n i = \\frac{n(n+1)}{2}
        $$
        </p>
        <table>
          <tr><th>Col A</th><th>Col B</th></tr>
          <tr><td>Data 1</td><td>Data 2</td></tr>
        </table>
        #### Skipped Subheading
        <p>Some more text.</p>
      </body>
    </html>
    """
    md, warnings = tn.normalize(raw)

    # Script removed
    assert "alert('xss')" not in md
    assert "malicious()" not in md

    # Math preserved
    assert "$x_1 * x_2 = y$" in md
    assert "\\sum_{i=1}^n i = \\frac{n(n+1)}{2}" in md
    assert "$100" in md

    # Table formatted
    assert "| Col A | Col B |" in md
    assert "| --- | --- |" in md
    assert "| Data 1 | Data 2 |" in md

    # Heading hierarchy fixed from #### to ##
    assert "## Skipped Subheading" in md


def test_toc_generation_and_injection():
    md = """# Introduction

## Overview
Text here.

### Architecture Details
More text.

## Vision OCR Pipeline
OCR text.

## Conclusion
Final notes.
"""
    toc = TOCGenerator.generate_toc(md)
    assert toc is not None
    assert "## Table of Contents" in toc
    assert "- [Overview](#overview)" in toc
    assert "  - [Architecture Details](#architecture-details)" in toc
    assert "- [Vision OCR Pipeline](#vision-ocr-pipeline)" in toc

    injected = TOCGenerator.inject_toc(md, toc)
    assert injected.startswith("# Introduction\n\n## Table of Contents")


def test_tag_extractor_and_frontmatter():
    md = """# Fast Machine Learning in Python

```python
import torch
print("Hello World")
```

This article covers KaTeX math formulas, Speech STT pipelines, and FastAPI server architecture.
"""
    tags = TagExtractor.extract_tags(md)
    assert "Python" in tags or "Katex" in tags or "Fastapi" in tags

    w_count, c_count = TagExtractor.calculate_word_and_char_count(md)
    assert w_count > 10
    assert c_count > 50

    read_time = TagExtractor.estimate_read_time(w_count)
    assert read_time == "1 min"

    fm = TagExtractor.generate_frontmatter("Fast ML", tags, w_count, read_time)
    assert fm.startswith("---\ntitle: \"Fast ML\"")

    with_fm = TagExtractor.inject_frontmatter(md, fm)
    assert with_fm.startswith("---\ntitle: \"Fast ML\"")
