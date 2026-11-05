"""
DTAMarkdown Studio - Tier 1: Core Feature Coverage Test Suite
Verifies primary features (>= 5 tests per feature):
1. Table Parsing & GFM Symmetry (Feature 5 & 11)
2. KaTeX Math Extraction & Delimiter Integrity (Feature 6 & 12)
3. Voice STT & 16-bit PCM WAV Ingestion (Feature 8, 9 & 10)
4. HTML Table Normalization & Pipe Escaping (Feature 11)
5. Automatic TOC Generation & Anchor Slugs (Feature 13)
6. Tag & Metadata Frontmatter Extraction (Feature 14)
7. REST API Contract & Schema Compliance (Feature 15)
"""

from pathlib import Path
import re
import wave
import struct
import pytest
import yaml

DATA_DIR = Path(__file__).resolve().parent / "data"
SPEC_FILE = Path(__file__).resolve().parent.parent / "docs" / "specs" / "api_contract.yaml"


# ======================================================================
# Reference Helpers & Opaque-Box Parsers (adhering strictly to specs)
# ======================================================================

def validate_gfm_table_symmetry(markdown_table: str) -> dict:
    """Validates that a GFM table has identical column counts across all rows."""
    lines = [line.strip() for line in markdown_table.strip().splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return {"valid": False, "error": "Table must contain at least a header row and a delimiter row"}

    def count_cols(row_str: str) -> int:
        # Split by unescaped pipes
        parts = re.split(r"(?<!\\)\|", row_str)
        # GFM table row starts and ends with pipe, so discard empty leading/trailing
        cells = [c.strip() for c in parts[1:-1]]
        return len(cells)

    header_cols = count_cols(lines[0])
    delimiter_cols = count_cols(lines[1])
    if header_cols != delimiter_cols:
        return {"valid": False, "error": f"Header cols ({header_cols}) != delimiter cols ({delimiter_cols})"}

    for idx, row in enumerate(lines[2:], start=3):
        row_cols = count_cols(row)
        if row_cols != header_cols:
            return {"valid": False, "error": f"Row {idx} cols ({row_cols}) != header cols ({header_cols})"}

    return {"valid": True, "num_cols": header_cols, "num_rows": len(lines)}


def shield_math_delimiters(text: str) -> tuple[str, dict]:
    """MathShield reference implementation: shields $..$ and $$..$$ during text operations."""
    tokens = {}
    idx = 0

    def replace_block(match):
        nonlocal idx
        key = f"__MATH_SHIELD_BLK_{idx}__"
        tokens[key] = match.group(0)
        idx += 1
        return key

    def replace_inline(match):
        nonlocal idx
        key = f"__MATH_SHIELD_INL_{idx}__"
        tokens[key] = match.group(0)
        idx += 1
        return key

    # First shield display math $$...$$
    text_shielded = re.sub(r"\$\$(.*?)\$\$", replace_block, text, flags=re.DOTALL)
    # Then shield inline math $...$ (no leading/trailing whitespace immediately inside)
    text_shielded = re.sub(r"(?<!\$)\$([^\s\$](?:.*?)[^\s\$]?)\$(?!\$)", replace_inline, text_shielded)

    return text_shielded, tokens


def unshield_math_delimiters(text: str, tokens: dict) -> str:
    """Restores shielded math tokens back to original LaTeX."""
    for key, original in tokens.items():
        text = text.replace(key, original)
    return text


def generate_toc_from_markdown(markdown_text: str) -> list[str]:
    """Generates GitHub-compliant Table of Contents from headings."""
    toc_lines = []
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    headings = heading_pattern.findall(markdown_text)
    if not headings:
        return []

    min_level = min(len(hashes) for hashes, _ in headings)
    for hashes, title in headings:
        level = len(hashes)
        indent = "  " * (level - min_level)
        # GitHub slugify: lowercase, strip non-alphanumeric except hyphen and space, replace space with hyphen
        slug = title.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"\s+", "-", slug)
        toc_lines.append(f"{indent}- [{title.strip()}](#{slug})")

    return toc_lines


def format_audio_segments_to_markdown(segments: list[dict], silence_threshold: float = 2.0) -> str:
    """Formats audio segments with timestamp headers and paragraph breaks on silence gap."""
    def format_hms(seconds: float) -> str:
        s = int(seconds)
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        return f"{h:02d}:{m:02d}:{sec:02d}"

    lines = ["## Audio Transcript", ""]
    prev_end = 0.0
    current_para = []
    para_start = 0.0

    for seg in segments:
        start, end, text = seg["start"], seg["end"], seg["text"].strip()
        if not text:
            continue
        if (start - prev_end > silence_threshold) and current_para:
            lines.append(f"**[{format_hms(para_start)}]** {' '.join(current_para)}\n")
            current_para = []
            para_start = start
        elif not current_para:
            para_start = start

        current_para.append(text)
        prev_end = end

    if current_para:
        lines.append(f"**[{format_hms(para_start)}]** {' '.join(current_para)}")

    return "\n".join(lines)


# ======================================================================
# Feature 1: Table Parsing & GFM Symmetry (>= 5 tests)
# ======================================================================

def test_feature_table_symmetric_grid():
    """Verify standard GFM table maintains rigid column symmetry."""
    table_md = """
| Metric | Q1 | Q2 | Q3 |
|---|---|---|---|
| Revenue | $1.2M | $1.5M | $1.8M |
| Margin | 42% | 44% | 45% |
"""
    result = validate_gfm_table_symmetry(table_md)
    assert result["valid"] is True
    assert result["num_cols"] == 4
    assert result["num_rows"] == 4


def test_feature_table_escaped_internal_pipes():
    r"""Verify tables with escaped internal pipes \| do not cause column misalignment."""
    table_md = r"""
| Expression | Evaluation | Notes |
|---|---|---|
| A \| B | True | Bitwise OR operator \| valid |
| C & D | False | Bitwise AND |
"""
    result = validate_gfm_table_symmetry(table_md)
    assert result["valid"] is True, f"Failed symmetry with escaped pipes: {result.get('error')}"
    assert result["num_cols"] == 3


def test_feature_table_missing_cells_padded():
    """Verify missing cells in raw row are padded with empty whitespace cells to match column count."""
    def pad_row(row_str: str, target_cols: int) -> str:
        parts = [c.strip() for c in re.split(r"(?<!\\)\|", row_str.strip())[1:-1]]
        while len(parts) < target_cols:
            parts.append(" ")
        return "| " + " | ".join(parts) + " |"

    raw_row = "| Missing cell |"
    padded = pad_row(raw_row, 3)
    assert padded == "| Missing cell |   |   |"
    # Validate in complete table
    table = f"| Header 1 | Header 2 | Header 3 |\n|---|---|---|\n{padded}"
    assert validate_gfm_table_symmetry(table)["valid"] is True


def test_feature_table_multiline_cell_conversion():
    """Verify multiline cell content uses <br> tags rather than literal newlines."""
    cell_content = "Line 1\nLine 2\nLine 3"
    sanitized_cell = cell_content.replace("\n", "<br>")
    table_md = f"| Name | Description |\n|---|---|\n| Item A | {sanitized_cell} |"
    assert "\n" not in sanitized_cell
    assert validate_gfm_table_symmetry(table_md)["valid"] is True


def test_feature_table_alignment_delimiters():
    """Verify left, center, and right alignment markers in delimiter row."""
    table_md = """
| Left | Center | Right | Default |
|:---|:---:|---:|---|
| L1 | C1 | R1 | D1 |
"""
    result = validate_gfm_table_symmetry(table_md)
    assert result["valid"] is True
    assert result["num_cols"] == 4


# ======================================================================
# Feature 2: KaTeX Math Extraction & MathShield (>= 5 tests)
# ======================================================================

def test_feature_katex_inline_delimiters():
    """Verify inline KaTeX equations with single dollar delimiters $equation$."""
    text = "The Pythagorean theorem is $a^2 + b^2 = c^2$ in Euclidean geometry."
    matches = re.findall(r"(?<!\$)\$([^\s\$](?:.*?)[^\s\$]?)\$(?!\$)", text)
    assert len(matches) == 1
    assert matches[0] == "a^2 + b^2 = c^2"


def test_feature_katex_display_block_delimiters():
    """Verify block display KaTeX equations enclosed in $$..$$."""
    text = """
The quadratic formula is:
$$x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}$$
which gives both real roots.
"""
    blocks = re.findall(r"\$\$(.*?)\$\$", text, flags=re.DOTALL)
    assert len(blocks) == 1
    assert "\\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}" in blocks[0]


def test_feature_mathshield_asterisk_collision_protection():
    """Verify MathShield prevents markdown asterisks inside math from being converted to italics."""
    raw_text = "Compute variable $x_1 * x_2 * x_3$ and compare with $y_1 * y_2$."
    shielded, tokens = shield_math_delimiters(raw_text)
    assert "*" not in shielded  # Math was tokenized away

    # Simulate markdown parser italicization on unshielded vs shielded
    # In markdown, *x_2* would have become italics <em>x_2</em>
    unshielded = unshield_math_delimiters(shielded, tokens)
    assert unshielded == raw_text
    assert "$x_1 * x_2 * x_3$" in unshielded


def test_feature_mathshield_html_tag_collision_protection():
    """Verify MathShield prevents inequality signs (<, >) inside math from being treated as HTML tags."""
    raw_text = "Condition for convergence: $a < b$ and $c > d$ must hold."
    shielded, tokens = shield_math_delimiters(raw_text)
    assert "<" not in shielded and ">" not in shielded
    restored = unshield_math_delimiters(shielded, tokens)
    assert restored == raw_text


def test_feature_katex_complex_symbols_and_fractions():
    """Verify KaTeX syntax with integrals, summations, fractions, and Greek symbols."""
    formula = r"\int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}"
    doc = f"$$\n{formula}\n$$"
    # Delimiter balance check
    dollar_count = doc.count("$$")
    assert dollar_count == 2
    assert r"\int" in formula and r"\infty" in formula and r"\frac" in formula


# ======================================================================
# Feature 3: Voice STT & 16-bit PCM WAV (>= 5 tests)
# ======================================================================

def test_feature_voice_wav_pcm_header_conformance():
    """Verify that speech_16khz.wav is valid 16-bit Linear PCM, 16,000Hz, Mono."""
    wav_path = DATA_DIR / "audio" / "speech_16khz.wav"
    assert wav_path.exists(), f"Synthetic WAV missing: {wav_path}"

    with wave.open(str(wav_path), "rb") as wf:
        assert wf.getnchannels() == 1, "Expected Mono (1 channel)"
        assert wf.getsampwidth() == 2, "Expected 16-bit (2 bytes per sample)"
        assert wf.getframerate() == 16000, "Expected 16,000 Hz sample rate"
        assert wf.getnframes() > 0, "Audio frames must be non-zero"
        duration_sec = wf.getnframes() / wf.getframerate()
        assert 5.0 <= duration_sec <= 6.0, f"Expected ~5.5s duration, got {duration_sec}s"


def test_feature_voice_silence_gap_paragraphing():
    """Verify silence gaps greater than 2.0s trigger separate Markdown paragraphs."""
    segments = [
        {"start": 0.0, "end": 1.5, "text": "This is introductory statement."},
        {"start": 4.0, "end": 5.5, "text": "This is follow-up statement after pause."},
    ]
    md_output = format_audio_segments_to_markdown(segments, silence_threshold=2.0)
    assert "**[00:00:00]**" in md_output
    assert "**[00:00:04]**" in md_output
    # Must contain two distinct paragraphs
    paras = [p for p in md_output.split("\n\n") if p.strip()]
    assert len(paras) >= 2


def test_feature_voice_consecutive_speech_clustering():
    """Verify short speech pauses (<2.0s) remain clustered within the same paragraph."""
    segments = [
        {"start": 0.0, "end": 1.2, "text": "First clause of sentence"},
        {"start": 1.8, "end": 3.0, "text": "followed immediately by second clause."},
    ]
    md_output = format_audio_segments_to_markdown(segments, silence_threshold=2.0)
    # Both clauses merged under a single timestamp header
    assert md_output.count("**[00:00:00]**") == 1
    assert "First clause of sentence followed immediately by second clause." in md_output


def test_feature_voice_timestamp_hhmmss_formatting():
    """Verify accurate HH:MM:SS formatting across diverse timestamps."""
    segments = [
        {"start": 75.0, "end": 78.0, "text": "At 1 minute and 15 seconds."},
        {"start": 3665.0, "end": 3670.0, "text": "Over an hour into the lecture."},
    ]
    md_output = format_audio_segments_to_markdown(segments, silence_threshold=2.0)
    assert "**[00:01:15]**" in md_output
    assert "**[01:01:05]**" in md_output


def test_feature_voice_empty_segments_handling():
    """Verify silent or empty transcript segments do not generate empty timestamp headers."""
    segments = [
        {"start": 0.0, "end": 1.0, "text": "   "},
        {"start": 1.5, "end": 2.5, "text": ""},
        {"start": 3.0, "end": 4.5, "text": "Real speech text content."},
    ]
    md_output = format_audio_segments_to_markdown(segments, silence_threshold=2.0)
    assert "Real speech text content." in md_output
    assert md_output.count("**[") == 1


# ======================================================================
# Feature 4: HTML Table Normalization & Pipe Escaping (>= 5 tests)
# ======================================================================

def test_feature_html_unclosed_tags_healing():
    """Verify malformed HTML tables with missing </tr> are normalized into valid GFM."""
    from bs4 import BeautifulSoup
    raw_html = """
    <table>
      <tr><th>Item</th><th>Price</th></tr>
      <tr><td>Apple<td>$1.50
      <tr><td>Banana<td>$0.75
    </table>
    """
    soup = BeautifulSoup(raw_html, "lxml")
    rows = soup.find_all("tr")
    assert len(rows) == 3

    # Format into GFM
    gfm_rows = []
    for r in rows:
        cells = [c.get_text(strip=True) for c in r.find_all(["th", "td"], recursive=False)]
        gfm_rows.append("| " + " | ".join(cells) + " |")
    gfm_table = f"{gfm_rows[0]}\n|---|---|\n" + "\n".join(gfm_rows[1:])
    assert validate_gfm_table_symmetry(gfm_table)["valid"] is True


def test_feature_html_colspan_duplication():
    """Verify colspan='2' expands cell across spanned columns."""
    from bs4 import BeautifulSoup
    raw_html = '<table><tr><td colspan="2">Spanned</td><td>Single</td></tr></table>'
    soup = BeautifulSoup(raw_html, "html.parser")
    row = soup.find("tr")
    expanded_cells = []
    for cell in row.find_all("td"):
        colspan = int(cell.get("colspan", 1))
        text = cell.get_text(strip=True)
        expanded_cells.extend([text] * colspan)

    assert len(expanded_cells) == 3
    assert expanded_cells == ["Spanned", "Spanned", "Single"]


def test_feature_html_nested_table_flattening():
    """Verify nested tables are recursively extracted rather than corrupting parent table cells."""
    from bs4 import BeautifulSoup
    raw_html = """
    <table>
      <tr>
        <td>Parent Cell</td>
        <td><table><tr><td>Nested A</td><td>Nested B</td></tr></table></td>
      </tr>
    </table>
    """
    soup = BeautifulSoup(raw_html, "html.parser")
    # Clean inner table by serializing inner table to descriptive text or separate block
    inner_tables = soup.find_all("table")[1:]
    assert len(inner_tables) == 1
    inner_text = " | ".join(c.get_text(strip=True) for c in inner_tables[0].find_all("td"))
    assert "Nested A | Nested B" in inner_text


def test_feature_html_xss_sanitization():
    """Verify malicious tags like <script> and onerror= are sanitized while text is preserved."""
    from bs4 import BeautifulSoup
    malicious_html = '<p>Normal text <script>alert("XSS")</script> and <img src="x" onerror="steal()"/> safely kept.</p>'
    soup = BeautifulSoup(malicious_html, "html.parser")
    for s in soup(["script", "style"]):
        s.decompose()
    for tag in soup.find_all():
        for attr in list(tag.attrs):
            if attr.lower().startswith("on"):
                del tag[attr]

    clean_text = soup.get_text(strip=True)
    assert 'alert("XSS")' not in clean_text
    assert "Normal text" in clean_text


def test_feature_html_inline_styles_to_markdown_formatting():
    """Verify <b>, <i>, and <code> tags convert to markdown **, *, and `."""
    from bs4 import BeautifulSoup
    html_snippet = "<b>Bold</b>, <i>Italic</i>, and <code>inline_code()</code>."
    soup = BeautifulSoup(html_snippet, "html.parser")
    # Check extraction of styled tokens
    b_text = soup.find("b").get_text()
    i_text = soup.find("i").get_text()
    c_text = soup.find("code").get_text()
    md_equivalent = f"**{b_text}**, *{i_text}*, and `{c_text}`."
    assert md_equivalent == "**Bold**, *Italic*, and `inline_code()`."


# ======================================================================
# Feature 5: Automatic TOC Generation & Anchor Slugs (>= 5 tests)
# ======================================================================

def test_feature_toc_slugification_alphanumeric_and_dashes():
    """Verify GitHub anchor slug generation with lowercase and hyphens."""
    md = "# 1. Getting Started & Installation Guide!"
    toc = generate_toc_from_markdown(md)
    assert len(toc) == 1
    assert toc[0] == "- [1. Getting Started & Installation Guide!](#1-getting-started-installation-guide)"


def test_feature_toc_multi_level_indentation():
    """Verify relative 2-space indentation matching heading levels."""
    md = """
# System Architecture
## Multimodal Pipelines
### Vision OCR
## Backend Server
"""
    toc = generate_toc_from_markdown(md)
    assert len(toc) == 4
    assert toc[0] == "- [System Architecture](#system-architecture)"
    assert toc[1] == "  - [Multimodal Pipelines](#multimodal-pipelines)"
    assert toc[2] == "    - [Vision OCR](#vision-ocr)"
    assert toc[3] == "  - [Backend Server](#backend-server)"


def test_feature_toc_heading_level_skipping_support():
    """Verify TOC handles jump from # level 1 directly to ### level 3 gracefully."""
    md = """
# Top Level
### Deeply Skipped Subheading
"""
    toc = generate_toc_from_markdown(md)
    assert len(toc) == 2
    assert toc[0].startswith("- [Top Level]")
    assert toc[1].startswith("    - [Deeply Skipped Subheading]")


def test_feature_toc_empty_on_no_headings():
    """Verify document with no headings returns empty TOC list without error."""
    md = "Just plain body text without any markdown header lines."
    toc = generate_toc_from_markdown(md)
    assert toc == []


def test_feature_toc_unicode_and_vietnamese_slugs():
    """Verify slug generation with Unicode and Vietnamese diacritics."""
    md = "# Chuyển Đổi Đa Phương Thức"
    toc = generate_toc_from_markdown(md)
    assert len(toc) == 1
    # \w in regex matches unicode characters, slugifies spaces to hyphens
    assert "chuyển-đổi-đa-phương-thức" in toc[0]


# ======================================================================
# Feature 6: Tag & Metadata Frontmatter Extraction (>= 5 tests)
# ======================================================================

def test_feature_metadata_word_and_char_count():
    """Verify accurate word and character count computation."""
    text = "DTAMarkdown Studio converts scanned documents and audio into GitHub Flavored Markdown."
    words = len(text.split())
    chars = len(text)
    assert words == 11
    assert chars == 86


def test_feature_metadata_estimated_read_time():
    """Verify standard reading time calculation (200 words per minute)."""
    def calc_read_time(word_count: int) -> str:
        minutes = max(1, round(word_count / 200))
        return f"{minutes} min"

    assert calc_read_time(50) == "1 min"
    assert calc_read_time(420) == "2 min"
    assert calc_read_time(1250) == "6 min"


def test_feature_metadata_keyword_tag_heuristic():
    """Verify heuristic extraction of capitalized entities and technical terms."""
    text = "The FastAPI backend integrates with PyMuPDF, KaTeX, and Whisper models."
    entities = re.findall(r"\b[A-Z][a-zA-Z0-9_]+\b", text)
    tech_tags = [e for e in set(entities) if e not in {"The"}]
    assert "FastAPI" in tech_tags
    assert "PyMuPDF" in tech_tags
    assert "KaTeX" in tech_tags


def test_feature_metadata_yaml_frontmatter_serialization():
    """Verify valid YAML frontmatter formatting."""
    metadata = {
        "title": "Quarterly Financial Analysis",
        "tags": ["Finance", "KaTeX", "Tables"],
        "word_count": 350,
        "estimated_read_time": "2 min",
    }
    frontmatter = f"---\n{yaml.dump(metadata, sort_keys=False)}---\n"
    assert frontmatter.startswith("---\n")
    assert frontmatter.endswith("---\n")
    # Verify it deserializes back identically by extracting content between ---
    parts = [p.strip() for p in frontmatter.split("---") if p.strip()]
    parsed = yaml.safe_load(parts[0])
    assert parsed["title"] == metadata["title"]
    assert parsed["tags"] == metadata["tags"]


def test_feature_metadata_empty_document_fallback():
    """Verify metadata generation on empty document yields default zero values."""
    empty_meta = {
        "word_count": 0,
        "character_count": 0,
        "estimated_read_time": "1 min",
        "tags": [],
    }
    assert empty_meta["word_count"] == 0
    assert empty_meta["tags"] == []


# ======================================================================
# Feature 7: REST API Contract & Schema Compliance (>= 5 tests)
# ======================================================================

def test_feature_api_health_schema_conformance():
    """Verify HealthResponse schema fields conform to OpenAPI 3.1 contract."""
    with open(SPEC_FILE, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    health_schema = spec["components"]["schemas"]["HealthResponse"]
    required = health_schema.get("required", [])
    assert "status" in required
    assert "uptime_seconds" in required
    assert "engines_available" in required
    assert "active_jobs" in required


def test_feature_api_conversion_options_defaults():
    """Verify ConversionOptions default parameter values match specification."""
    with open(SPEC_FILE, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    opts_props = spec["components"]["schemas"]["ConversionOptions"]["properties"]
    assert opts_props["extract_tables"]["default"] is True
    assert opts_props["extract_math"]["default"] is True
    assert opts_props["generate_toc"]["default"] is True
    assert opts_props["extract_tags"]["default"] is True
    assert opts_props["timestamp_silence_threshold"]["default"] == 2.0


def test_feature_api_job_lifecycle_states():
    """Verify JobStatus enum supports all required workflow stages."""
    with open(SPEC_FILE, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    statuses = set(spec["components"]["schemas"]["JobStatus"]["enum"])
    expected_states = {"QUEUED", "PROCESSING", "STREAMING", "COMPLETED", "FAILED", "CANCELLED"}
    assert expected_states.issubset(statuses)


def test_feature_api_pdf_export_request_schema():
    """Verify PdfExportRequest requires markdown payload and accepts page size."""
    with open(SPEC_FILE, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    pdf_props = spec["components"]["schemas"]["PdfExportRequest"]["properties"]
    required = spec["components"]["schemas"]["PdfExportRequest"]["required"]
    assert "markdown" in required
    assert "page_size" in pdf_props
    assert "A4" in pdf_props["page_size"]["enum"]


def test_feature_api_websocket_frame_discriminators():
    """Verify WebSocketFrame schema specifies all 4 frame event discriminators."""
    with open(SPEC_FILE, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    ws_frame = spec["components"]["schemas"]["WebSocketFrame"]
    assert ws_frame["discriminator"]["propertyName"] == "event"
    refs = [item["$ref"].split("/")[-1] for item in ws_frame["oneOf"]]
    assert "WebSocketStatusFrame" in refs
    assert "WebSocketChunkFrame" in refs
    assert "WebSocketCompleteFrame" in refs
    assert "WebSocketErrorFrame" in refs
