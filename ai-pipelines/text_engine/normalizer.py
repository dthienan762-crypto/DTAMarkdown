"""
DTAMarkdown Studio - Text & Table Normalization Engine
Converts raw unstructured text, malformed HTML, and messy documents into
pristine GitHub Flavored Markdown (GFM).
Handles nested tables, colspan/rowspan, escaped pipes, and header hierarchy.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple
from bs4 import BeautifulSoup, Tag
import markdownify

from .math_shield import MathShield


class TableNormalizer:
    """
    Robust HTML table parser and AST transformer.
    Flattens nested tables, resolves colspan and rowspan, escapes pipe characters,
    and produces rigid GFM markdown tables with symmetrical column counts.
    """

    @classmethod
    def clean_cell_text(cls, text: str) -> str:
        """Sanitizes text inside a table cell for GFM compatibility."""
        if not text:
            return ""
        # Convert internal newlines to <br> to prevent breaking Markdown table rows
        cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
        cleaned = re.sub(r"\n+", "<br>", cleaned)
        # Escape raw pipe characters that are not already escaped
        cleaned = re.sub(r"(?<!\\)\|", r"\|", cleaned)
        # Collapse multiple horizontal whitespaces
        cleaned = re.sub(r"[ \t]+", " ", cleaned).strip()
        return cleaned

    @classmethod
    def html_table_to_gfm(cls, table_tag: Tag) -> str:
        """
        Converts a BeautifulSoup <table> tag into standard GFM Markdown.
        Resolves nested tables, colspan, and rowspan via a 2D coordinate grid.
        """
        # 1. Flatten any inner nested tables first
        nested_tables = table_tag.find_all("table")
        for inner in nested_tables:
            if inner is not table_tag:
                # Replace inner table with text representation of its contents
                inner_rows = []
                for tr in inner.find_all("tr"):
                    cell_texts = [td.get_text(separator=" ", strip=True) for td in tr.find_all(["th", "td"])]
                    if cell_texts:
                        inner_rows.append("; ".join(cell_texts))
                inner_summary = " [" + " | ".join(inner_rows) + "] " if inner_rows else ""
                inner.replace_with(inner_summary)

        # 2. Extract rows
        rows = table_tag.find_all("tr")
        if not rows:
            return ""

        # 3. Build a 2D grid matrix resolving rowspan and colspan
        grid: List[List[Optional[str]]] = []

        for r_idx, tr in enumerate(rows):
            # Ensure grid has enough rows
            while len(grid) <= r_idx:
                grid.append([])

            c_idx = 0
            cells = tr.find_all(["th", "td"], recursive=False)
            if not cells:
                # Sometimes <tr> contains cells inside other wrappers
                cells = tr.find_all(["th", "td"])

            for cell in cells:
                # Advance c_idx to the next unfilled slot in this row
                while c_idx < len(grid[r_idx]) and grid[r_idx][c_idx] is not None:
                    c_idx += 1

                # Parse colspan & rowspan attributes
                try:
                    colspan = int(cell.get("colspan", 1))
                except (ValueError, TypeError):
                    colspan = 1
                try:
                    rowspan = int(cell.get("rowspan", 1))
                except (ValueError, TypeError):
                    rowspan = 1

                colspan = max(1, min(colspan, 50))
                rowspan = max(1, min(rowspan, 50))

                cell_raw_text = cell.get_text(separator="\n", strip=True)
                cleaned_text = cls.clean_cell_text(cell_raw_text)

                # Fill slots across rowspan and colspan
                for dr in range(rowspan):
                    target_r = r_idx + dr
                    while len(grid) <= target_r:
                        grid.append([])

                    for dc in range(colspan):
                        target_c = c_idx + dc
                        # Extend target row with None up to target_c
                        while len(grid[target_r]) <= target_c:
                            grid[target_r].append(None)

                        if dr == 0 and dc == 0:
                            grid[target_r][target_c] = cleaned_text
                        else:
                            # Pad merged span cells with empty string
                            grid[target_r][target_c] = ""

                c_idx += colspan

        # 4. Normalize grid width across all rows
        max_cols = 0
        for row in grid:
            max_cols = max(max_cols, len(row))

        if max_cols == 0:
            return ""

        normalized_rows: List[List[str]] = []
        for row in grid:
            norm_row = []
            for c in range(max_cols):
                val = row[c] if c < len(row) and row[c] is not None else ""
                norm_row.append(val)
            normalized_rows.append(norm_row)

        if not normalized_rows:
            return ""

        # 5. Format GFM table string
        md_lines = []
        header_row = normalized_rows[0]
        # Replace empty headers with generic Col X if all are empty
        if all(c == "" for c in header_row):
            header_row = [f"Col {i+1}" for i in range(max_cols)]

        md_lines.append("| " + " | ".join(header_row) + " |")
        md_lines.append("| " + " | ".join(["---"] * max_cols) + " |")

        # Body rows (from index 1 onwards)
        body_rows = normalized_rows[1:]
        if not body_rows:
            # If there was only 1 row, duplicate it as body or add empty row
            body_rows = [[""] * max_cols]

        for b_row in body_rows:
            md_lines.append("| " + " | ".join(b_row) + " |")

        return "\n" + "\n".join(md_lines) + "\n"


class TextNormalizer:
    """
    Complete Text and HTML normalization engine.
    Sanitizes HTML tags, protects LaTeX formulas with MathShield,
    formats tables into GFM, fixes heading depth skips, and cleans unicode artifacts.
    """

    DANGEROUS_TAGS = {"script", "style", "iframe", "object", "embed", "applet", "meta", "link"}
    DANGEROUS_ATTRS = re.compile(r"^on[a-z]+", re.IGNORECASE)

    def __init__(self):
        self.math_shield = MathShield()

    def sanitize_html_dom(self, soup: BeautifulSoup) -> None:
        """Removes dangerous tags and inline javascript event handlers."""
        for tag_name in self.DANGEROUS_TAGS:
            for elem in soup.find_all(tag_name):
                elem.decompose()

        for tag in soup.find_all(True):
            # Remove on* event handlers (e.g. onload, onerror)
            attrs_to_remove = [attr for attr in tag.attrs if self.DANGEROUS_ATTRS.match(attr)]
            for attr in attrs_to_remove:
                del tag.attrs[attr]

            # Strip javascript: URLs
            for url_attr in ["href", "src"]:
                if url_attr in tag.attrs:
                    val = str(tag.attrs[url_attr]).strip()
                    if val.lower().startswith("javascript:") or val.lower().startswith("data:text/html"):
                        tag.attrs[url_attr] = "#"

    def clean_unicode(self, text: str) -> str:
        """Strips zero-width spaces, normalizes non-breaking spaces and line endings."""
        if not text:
            return ""
        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Replace non-breaking spaces with standard space
        text = text.replace("\u00a0", " ")
        # Strip zero-width spaces and control formatting chars
        text = re.sub(r"[\u200B\u200C\u200D\uFEFF\u200E\u200F\u202A-\u202E]", "", text)
        # Strip non-printable ASCII control characters except \n, \t
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
        return text

    def fix_heading_hierarchy(self, markdown: str) -> str:
        """
        Adjusts skipped heading depths (e.g., `# Title` immediately followed by `#### Subheading`
        adjusted to `## Subheading`).
        """
        lines = markdown.split("\n")
        adjusted_lines = []
        last_level = 0

        for line in lines:
            m = re.match(r"^(#{1,6})\s+(.*)$", line)
            if m:
                level = len(m.group(1))
                title = m.group(2)
                if last_level == 0:
                    target_level = level
                elif level > last_level + 1:
                    target_level = last_level + 1
                else:
                    target_level = level
                last_level = target_level
                adjusted_lines.append(f"{'#' * target_level} {title}")
            else:
                adjusted_lines.append(line)

        return "\n".join(adjusted_lines)

    def normalize(self, raw_text: str, extract_tables: bool = True, extract_math: bool = True) -> Tuple[str, List[str]]:
        """
        Full end-to-end normalization pipeline.
        Returns:
            normalized_markdown: clean GFM markdown.
            warnings: list of non-fatal warnings encountered.
        """
        warnings: List[str] = []
        if not raw_text or not raw_text.strip():
            return "", warnings

        # Step 1: Clean unicode anomalies
        cleaned = self.clean_unicode(raw_text)

        # Step 2: Math Shield phase
        shield_tokens = []
        if extract_math:
            cleaned, shield_tokens = self.math_shield.shield(cleaned)
            is_valid, math_warnings = self.math_shield.validate_delimiters(raw_text)
            warnings.extend(math_warnings)

        # Step 3: Check if input is or contains HTML
        has_html_tags = bool(re.search(r"<[a-z/][\s\S]*?>", cleaned, re.IGNORECASE))

        if has_html_tags:
            soup = BeautifulSoup(cleaned, "html.parser")
            self.sanitize_html_dom(soup)

            # Process tables with dedicated TableNormalizer
            if extract_tables:
                tables = soup.find_all("table")
                for table in tables:
                    gfm_table = TableNormalizer.html_table_to_gfm(table)
                    table.replace_with(soup.new_string(gfm_table))

            # Convert remaining HTML to Markdown using markdownify
            html_str = str(soup)
            md = markdownify.markdownify(
                html_str,
                heading_style="ATX",
                strip=["meta", "link"],
                code_language=""
            )
        else:
            # Plain text input
            md = cleaned

        # Step 4: Math Unshield phase
        if extract_math and shield_tokens:
            md = self.math_shield.unshield(md, shield_tokens)

        # Step 5: Fix heading hierarchy
        md = self.fix_heading_hierarchy(md)

        # Step 6: Post-processing whitespace normalization
        # Collapse 3+ consecutive newlines down to 2
        md = re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"

        return md, warnings
