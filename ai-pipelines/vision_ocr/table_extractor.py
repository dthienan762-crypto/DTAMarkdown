"""
DTAMarkdown Studio - Table Extractor (Vision OCR)
Preserves tabular structure, extracts rows and columns, and formats
strictly aligned GitHub Flavored Markdown (GFM) tables.
"""

from __future__ import annotations

import re
from typing import Any, List, Optional, Tuple


class TableExtractor:
    """
    Extracts tabular structures from PyMuPDF document pages or raw OCR text blocks
    and transforms them into strictly compliant GFM tables without column misalignment.
    """

    @classmethod
    def clean_cell(cls, cell_text: Optional[str]) -> str:
        """Sanitizes text inside a table cell for GFM compatibility."""
        if cell_text is None:
            return ""
        text = str(cell_text).strip()
        # Convert internal newlines to <br> to prevent breaking Markdown table row structure
        text = re.sub(r"[\r\n]+", "<br>", text)
        # Escape raw pipe characters
        text = re.sub(r"(?<!\\)\|", r"\|", text)
        # Collapse multiple horizontal whitespaces
        text = re.sub(r"[ \t]+", " ", text).strip()
        return text

    @classmethod
    def format_grid_to_gfm(cls, rows: List[List[Any]], has_header: bool = True) -> str:
        """
        Transforms a 2D list of cells into a perfectly aligned GFM Markdown table.
        Ensures identical column counts across all rows, padding missing cells with whitespace.
        """
        if not rows:
            return ""

        # 1. Clean all cells and calculate maximum column count
        cleaned_rows: List[List[str]] = []
        max_cols = 0
        for row in rows:
            cleaned_row = [cls.clean_cell(c) for c in row]
            max_cols = max(max_cols, len(cleaned_row))
            cleaned_rows.append(cleaned_row)

        if max_cols == 0:
            return ""

        # 2. Pad rows so that every row has exactly max_cols cells
        padded_rows: List[List[str]] = []
        for row in cleaned_rows:
            padded = list(row)
            while len(padded) < max_cols:
                padded.append("")
            padded_rows.append(padded)

        # 3. Determine header
        md_lines = []
        header = padded_rows[0]
        # If all header cells are empty, generate generic column headers
        if all(c == "" for c in header):
            header = [f"Column {i + 1}" for i in range(max_cols)]

        md_lines.append("| " + " | ".join(header) + " |")
        md_lines.append("| " + " | ".join(["---"] * max_cols) + " |")

        # 4. Body rows
        body_rows = padded_rows[1:] if len(padded_rows) > 1 else []
        for b_row in body_rows:
            md_lines.append("| " + " | ".join(b_row) + " |")

        return "\n" + "\n".join(md_lines) + "\n"

    @classmethod
    def extract_tables_from_pdf_page(cls, page: Any) -> Tuple[List[str], List[Any]]:
        """
        Uses PyMuPDF's page.find_tables() to identify tabular structures and their bounding boxes.
        Returns:
            tables_gfm: list of GFM table markdown strings.
            table_rects: list of PyMuPDF bounding rects for exclusion during regular text extraction.
        """
        tables_gfm: List[str] = []
        table_rects: List[Any] = []

        if not hasattr(page, "find_tables"):
            return tables_gfm, table_rects

        try:
            tabs = page.find_tables()
            for tab in tabs:
                extracted = tab.extract()
                if extracted and len(extracted) >= 1:
                    gfm = cls.format_grid_to_gfm(extracted)
                    if gfm.strip():
                        tables_gfm.append(gfm)
                        table_rects.append(tab.bbox)
        except Exception:
            # Fallback if page layout analysis encounters an anomaly
            pass

        return tables_gfm, table_rects

    @classmethod
    def repair_raw_markdown_table(cls, table_block: str) -> str:
        """
        Repairs an existing raw markdown table string by enforcing equal column count
        and fixing broken delimiters.
        """
        lines = [line.strip() for line in table_block.strip().split("\n") if line.strip()]
        if len(lines) < 2:
            return table_block

        # Parse rows by unescaped pipe
        parsed_rows = []
        for line in lines:
            # Strip leading and trailing pipe
            core = line
            if core.startswith("|"):
                core = core[1:]
            if core.endswith("|"):
                core = core[:-1]
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", core)]
            parsed_rows.append(cells)

        max_cols = max(len(r) for r in parsed_rows)
        if max_cols == 0:
            return table_block

        header = parsed_rows[0]
        while len(header) < max_cols:
            header.append(f"Col {len(header) + 1}")

        md_lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * max_cols) + " |"]

        # Body rows (skip delimiter row if it was line 1)
        start_idx = 1
        if len(parsed_rows) > 1 and all(re.match(r"^:?-+:?$", c) for c in parsed_rows[1] if c):
            start_idx = 2

        for r in parsed_rows[start_idx:]:
            row_padded = list(r)
            while len(row_padded) < max_cols:
                row_padded.append("")
            # Clean each cell
            cleaned_row = [cls.clean_cell(c) for c in row_padded]
            md_lines.append("| " + " | ".join(cleaned_row) + " |")

        return "\n".join(md_lines)
