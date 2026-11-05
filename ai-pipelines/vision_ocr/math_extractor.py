"""
DTAMarkdown Studio - Math Formula Extractor (Vision OCR)
Extracts mathematical formulas into KaTeX/LaTeX format ($..$ and $$..$$),
cleans whitespace around delimiters, and normalizes LaTeX syntax.
"""

from __future__ import annotations

import re
from typing import List, Tuple


class MathExtractor:
    """
    Extracts and standardizes KaTeX mathematical formulas:
    - Inline formulas: $equation$ (no whitespace immediately adjacent to $).
    - Display formulas: $$equation$$ (block equations on dedicated lines).
    """

    LATEX_KEYWORDS = [
        r"\\frac", r"\\sqrt", r"\\sum", r"\\int", r"\\prod", r"\\lim",
        r"\\alpha", r"\\beta", r"\\gamma", r"\\theta", r"\\pi", r"\\sigma",
        r"\\partial", r"\\infty", r"\\pm", r"\\times", r"\\cdot", r"\\leq", r"\\geq"
    ]

    LATEX_PATTERN = re.compile(r"(" + "|".join(LATEX_KEYWORDS) + r")")

    @classmethod
    def clean_katex_delimiters(cls, text: str) -> str:
        """
        Ensures KaTeX inline formulas have no leading/trailing spaces inside $ delimiters:
        e.g. '$ x + y $' -> '$x + y$'.
        Ensures block formulas are properly formatted:
        e.g. '$$ equation $$' -> '$$\nequation\n$$'.
        """
        if not text:
            return ""

        # 1. Clean block delimiters $$ ... $$
        def clean_block(match: re.Match) -> str:
            content = match.group(1).strip()
            return f"\n$$\n{content}\n$$\n"

        text = re.sub(r"\$\$\s*([\s\S]*?)\s*\$\$", clean_block, text)

        # 2. Clean inline delimiters $ ... $
        def clean_inline(match: re.Match) -> str:
            content = match.group(1).strip()
            # Guard against currency amounts
            if re.match(r"^\d+(?:,\d+)*(?:\.\d+)?$", content):
                return match.group(0)
            return f"${content}$"

        text = re.sub(r"(?<![\$\w\\])\$\s*([^\$\n\r]+?)\s*\$(?![\$\w])", clean_inline, text)

        return text

    @classmethod
    def wrap_raw_latex_equations(cls, text: str) -> str:
        """
        Detects standalone lines containing prominent LaTeX markup that were not
        enclosed in delimiters and wraps them in $$...$$.
        """
        if not text:
            return ""

        lines = text.split("\n")
        new_lines: List[str] = []

        in_block = False
        for line in lines:
            stripped = line.strip()

            if "$$" in stripped:
                in_block = not in_block
                new_lines.append(line)
                continue

            if in_block:
                new_lines.append(line)
                continue

            # Check if line looks like an unwrapped display formula
            if cls.LATEX_PATTERN.search(stripped) and not stripped.startswith("$") and not stripped.endswith("$"):
                # Must not look like standard markdown text
                if not re.match(r"^[#*-]\s+", stripped) and len(stripped.split()) <= 20:
                    new_lines.append(f"$$\n{stripped}\n$$")
                    continue

            new_lines.append(line)

        return "\n".join(new_lines)
