"""
DTAMarkdown Studio - Table of Contents Generator
Scans Markdown headings and automatically generates hierarchical Table of Contents
with GitHub-compatible slug anchors.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple


def generate_github_slug(title: str, existing_slugs: Dict[str, int]) -> str:
    """
    Generates a GitHub-compatible markdown heading anchor slug.
    Strips punctuation, replaces spaces with hyphens, and handles collisions.
    """
    # 1. Lowercase
    slug = title.strip().lower()
    # 2. Remove markdown formatting like **bold**, *italic*, `code`, [link text](url)
    slug = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", slug)
    slug = re.sub(r"[*_`]", "", slug)
    # 3. Remove characters that are not alphanumeric, spaces, or hyphens
    slug = re.sub(r"[^\w\s-]", "", slug)
    # 4. Replace whitespace with hyphens
    slug = re.sub(r"\s+", "-", slug).strip("-")
    if not slug:
        slug = "section"

    # 5. Handle duplicate anchors
    if slug in existing_slugs:
        existing_slugs[slug] += 1
        return f"{slug}-{existing_slugs[slug]}"
    else:
        existing_slugs[slug] = 0
        return slug


class TOCGenerator:
    """
    Analyzes markdown headings to construct a nested Table of Contents.
    """

    HEADING_REGEX = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    @classmethod
    def extract_headings(cls, markdown: str) -> List[Tuple[int, str, str]]:
        """
        Extracts list of (level, title, slug) from markdown text.
        Skips headings inside fenced code blocks.
        """
        if not markdown:
            return []

        # Strip out code blocks before heading extraction
        code_block_mask = re.compile(r"```[\s\S]*?```")
        cleaned_md = code_block_mask.sub("", markdown)

        headings: List[Tuple[int, str, str]] = []
        slug_counts: Dict[str, int] = {}

        for line in cleaned_md.split("\n"):
            line_str = line.strip()
            match = re.match(r"^(#{1,6})\s+(.+)$", line_str)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()
                # Do not index "Table of Contents" heading itself
                if title.lower() in ("table of contents", "mục lục", "toc"):
                    continue
                slug = generate_github_slug(title, slug_counts)
                headings.append((level, title, slug))

        return headings

    @classmethod
    def generate_toc(cls, markdown: str, min_headings: int = 2) -> Optional[str]:
        """
        Generates Table of Contents Markdown block.
        Returns None if fewer than min_headings are present.
        """
        headings = cls.extract_headings(markdown)
        if len(headings) < min_headings:
            return None

        min_level = min(h[0] for h in headings)
        toc_lines = ["## Table of Contents", ""]

        for level, title, slug in headings:
            indent_depth = max(0, level - min_level)
            indent = "  " * indent_depth
            toc_lines.append(f"{indent}- [{title}](#{slug})")

        return "\n".join(toc_lines)

    @classmethod
    def inject_toc(cls, markdown: str, toc: str) -> str:
        """
        Injects TOC into the Markdown document in an optimal position:
        - After YAML frontmatter (if present)
        - After first # Title heading (if present)
        - Or at the very top.
        """
        if not toc:
            return markdown

        # Check for YAML frontmatter
        frontmatter_match = re.match(r"^---\n[\s\S]*?\n---\n*", markdown)
        if frontmatter_match:
            end_fm = frontmatter_match.end()
            fm_part = markdown[:end_fm].rstrip() + "\n\n"
            rest = markdown[end_fm:].lstrip()

            # Check if rest begins with a top-level title
            title_match = re.match(r"^#\s+[^\n]+\n*", rest)
            if title_match:
                end_title = title_match.end()
                title_part = rest[:end_title].rstrip()
                remaining = rest[end_title:].lstrip()
                return f"{fm_part}{title_part}\n\n{toc}\n\n{remaining}"
            else:
                return f"{fm_part}{toc}\n\n{rest}"

        # No frontmatter: check if starts with top-level # Title
        title_match = re.match(r"^#\s+[^\n]+\n*", markdown)
        if title_match:
            end_title = title_match.end()
            title_part = markdown[:end_title].rstrip()
            remaining = markdown[end_title:].lstrip()
            return f"{title_part}\n\n{toc}\n\n{remaining}"

        return f"{toc}\n\n{markdown.lstrip()}"
