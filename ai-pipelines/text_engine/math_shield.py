"""
DTAMarkdown Studio - MathShield
Protects KaTeX / LaTeX mathematical formulas ($..$ and $$..$$) during
HTML parsing, markdownify transformations, and text normalization.
"""

from __future__ import annotations

import re
from typing import List, Tuple


class MathShield:
    """
    Two-phase math delimiter shielding:
    1. Shield Phase: Replaces inline $...$ and block $$...$$ with inert alphanumeric tokens.
       Alphanumeric tokens prevent markdown parsers (like markdownify) from escaping underscores or mangling formulas.
    2. Unshield Phase: Restores pristine LaTeX formulas into the normalized Markdown stream.
    """

    # Matches block math: $$...$$ (allows multiline)
    BLOCK_PATTERN = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)

    # Matches inline math: $...$
    # Must not be preceded or followed by another $, must not span multiple paragraphs,
    # and ignores pure currency amounts ($10, $20.50, $1,000).
    INLINE_PATTERN = re.compile(r"(?<![\$\w\\])\$([^\$\n\r]+?)\$(?![\$\w])")

    def __init__(self, token_prefix: str = "KATEXSHIELD"):
        self.token_prefix = token_prefix

    def shield(self, text: str) -> Tuple[str, List[Tuple[str, str, bool]]]:
        """
        Shields all math formulas with unique alphanumeric tokens.
        Returns:
            shielded_text: text with tokens in place of formulas.
            tokens: list of (token_string, original_latex_including_delimiters, is_block)
        """
        if not text:
            return "", []

        tokens: List[Tuple[str, str, bool]] = []
        token_counter = 0

        # Step 1: Shield Block Math $$...$$ first to prevent inline $ from matching outer $$
        def replace_block(match: re.Match) -> str:
            nonlocal token_counter
            full_match = match.group(0)
            token = f"{self.token_prefix}BLK{token_counter}END"
            token_counter += 1
            tokens.append((token, full_match, True))
            return token

        shielded = self.BLOCK_PATTERN.sub(replace_block, text)

        # Step 2: Shield Inline Math $...$
        def replace_inline(match: re.Match) -> str:
            nonlocal token_counter
            full_match = match.group(0)
            inner = match.group(1).strip()

            # Guard against currency amounts (e.g. "$20" or "$ 50" or "$1,000.00")
            if re.match(r"^\d+(?:,\d+)*(?:\.\d+)?$", inner):
                return full_match

            token = f"{self.token_prefix}INL{token_counter}END"
            token_counter += 1
            tokens.append((token, full_match, False))
            return token

        shielded = self.INLINE_PATTERN.sub(replace_inline, shielded)

        return shielded, tokens

    def unshield(self, text: str, tokens: List[Tuple[str, str, bool]]) -> str:
        """
        Restores original LaTeX formulas from shielded tokens.
        Handles both literal tokens and any escaped variants.
        """
        if not text or not tokens:
            return text

        result = text
        for token, original, _is_block in tokens:
            result = result.replace(token, original)
            # Also handle if markdown parser escaped any part of token
            escaped_token = re.escape(token)
            if escaped_token != token:
                result = re.sub(escaped_token, original, result)
        return result

    @staticmethod
    def validate_delimiters(text: str) -> Tuple[bool, List[str]]:
        """
        Validates delimiter pairing symmetry ($ and $$).
        Returns:
            is_valid: True if no unclosed or dangling math delimiters found.
            warnings: list of diagnostic warning strings.
        """
        warnings = []
        if not text:
            return True, warnings

        # 1. Count $$ occurrences (must be even)
        double_dollar_count = len(re.findall(r"\$\$", text))
        if double_dollar_count % 2 != 0:
            warnings.append(f"Odd number of display math ($$) delimiters detected ({double_dollar_count}). Potential unclosed block formula.")

        # Strip out code blocks and block math to count inline $
        temp = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
        temp = re.sub(r"`.*?`", "", temp)
        temp = re.sub(r"\$\$.*?\$\$", "", temp, flags=re.DOTALL)

        # Count single $ that are not escaped (\$) and not immediately followed by digit (currency)
        single_dollar_candidates = re.findall(r"(?<!\\)\$(?!\d)", temp)
        if len(single_dollar_candidates) % 2 != 0:
            warnings.append(f"Unpaired inline math ($) delimiter detected ({len(single_dollar_candidates)} unescaped non-currency dollar signs).")

        return len(warnings) == 0, warnings
