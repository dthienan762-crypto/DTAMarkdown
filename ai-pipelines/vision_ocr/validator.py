"""
DTAMarkdown Studio - Post-Processor Validator (Vision OCR)
Validates table column count symmetry, delimiter consistency,
and KaTeX equation delimiter symmetry ($ and $$).
"""

from __future__ import annotations

import re
from typing import List, Tuple
from .table_extractor import TableExtractor
from .math_extractor import MathExtractor


class PostProcessorValidator:
    """
    Validates and repairs OCR Markdown output:
    1. Table structural validation (header == delimiter == data row column count).
    2. KaTeX delimiter pairing and syntax symmetry validation.
    """

    @classmethod
    def validate_and_repair_tables(cls, markdown: str) -> Tuple[str, List[str]]:
        """
        Scans document for markdown table blocks and validates column count symmetry.
        Auto-repairs mismatched column counts and fixes broken delimiters.
        """
        warnings: List[str] = []
        if not markdown or "|" not in markdown:
            return markdown, warnings

        lines = markdown.split("\n")
        new_lines: List[str] = []
        table_buffer: List[str] = []
        in_table = False

        for line in lines:
            stripped = line.strip()
            # Detect table line: starts and ends with pipe, or contains multiple pipes
            is_table_line = (
                (stripped.startswith("|") and stripped.endswith("|")) or
                (stripped.count("|") >= 2 and not stripped.startswith("```"))
            )

            if is_table_line:
                in_table = True
                table_buffer.append(stripped)
            else:
                if in_table and table_buffer:
                    # Flush and validate buffered table
                    repaired_table = TableExtractor.repair_raw_markdown_table("\n".join(table_buffer))
                    # Check if original had mismatched columns
                    orig_counts = [len(re.split(r"(?<!\\)\|", r.strip("|"))) for r in table_buffer]
                    if len(set(orig_counts)) > 1:
                        warnings.append(f"Table with inconsistent column counts detected ({orig_counts}). Automatically normalized to GFM symmetry.")
                    new_lines.append(repaired_table)
                    table_buffer = []
                    in_table = False
                new_lines.append(line)

        if in_table and table_buffer:
            repaired_table = TableExtractor.repair_raw_markdown_table("\n".join(table_buffer))
            new_lines.append(repaired_table)

        return "\n".join(new_lines), warnings

    @classmethod
    def validate_and_repair_katex(cls, markdown: str) -> Tuple[str, List[str]]:
        """
        Validates KaTeX equation delimiters ($ and $$).
        Repairs spacing around delimiters and auto-closes dangling formula blocks.
        """
        warnings: List[str] = []
        if not markdown:
            return markdown, warnings

        # 1. Clean spacing around math delimiters
        cleaned_md = MathExtractor.clean_katex_delimiters(markdown)

        # 2. Check $$ count
        double_dollar_count = len(re.findall(r"\$\$", cleaned_md))
        if double_dollar_count % 2 != 0:
            warnings.append(f"Unpaired display math ($$) delimiter detected. Auto-appending closing $$ to maintain preview integrity.")
            cleaned_md = cleaned_md.rstrip() + "\n$$\n"

        # 3. Check inline $ count (excluding escaped \$ and currency $10)
        temp = re.sub(r"```[\s\S]*?```", "", cleaned_md)
        temp = re.sub(r"`[^`]*`", "", temp)
        temp = re.sub(r"\$\$[\s\S]*?\$\$", "", temp)
        inline_dollars = re.findall(r"(?<!\\)\$(?!\d)", temp)

        if len(inline_dollars) % 2 != 0:
            warnings.append(f"Unpaired inline math ($) delimiter detected ({len(inline_dollars)} unescaped non-currency dollar signs).")

        return cleaned_md, warnings

    @classmethod
    def validate_and_repair(cls, markdown: str) -> Tuple[str, List[str]]:
        """
        Runs comprehensive post-processing validation and repairs.
        Returns:
            repaired_markdown: structurally sound GFM Markdown.
            warnings: list of diagnostic warnings.
        """
        warnings: List[str] = []
        md, table_warnings = cls.validate_and_repair_tables(markdown)
        warnings.extend(table_warnings)

        md, katex_warnings = cls.validate_and_repair_katex(md)
        warnings.extend(katex_warnings)

        return md, warnings
