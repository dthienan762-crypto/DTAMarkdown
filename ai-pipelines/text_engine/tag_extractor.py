"""
DTAMarkdown Studio - Tag & Metadata Extractor
Analyzes document text to extract keyword tags, calculate word count and estimated
reading time, and generates clean YAML frontmatter.
"""

from __future__ import annotations

from collections import Counter
import math
import re
from typing import Any, Dict, List, Optional, Set


STOPWORDS: Set[str] = {
    # English common stop words
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't",
    "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have",
    "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into",
    "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our",
    "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's",
    "should", "shouldn't", "so", "some", "such", "than", "that", "that's", "the", "their", "theirs",
    "them", "themselves", "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't",
    "we", "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's",
    "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with", "won't",
    "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
    "yourselves",
    # Common document noise
    "true", "false", "null", "none", "section", "table", "item", "page", "value",
    # Vietnamese common stop words
    "và", "của", "cho", "các", "những", "được", "trong", "với", "là", "có", "khi", "này", "đó",
    "về", "từ", "ra", "đã", "sẽ", "đang", "để", "như", "theo", "thì", "tại", "nhiều", "một", "hai"
}

TECH_KEYWORDS: Set[str] = {
    "python", "typescript", "javascript", "react", "katex", "latex", "ocr", "whisper", "fastapi",
    "markdown", "html", "onnx", "pymupdf", "docker", "rest", "websocket", "streaming", "sql",
    "table", "audio", "vision", "speech", "pdf", "gemini", "ai", "machine learning"
}


class TagExtractor:
    """
    Extracts tags, word/char counts, reading time, and generates YAML frontmatter.
    """

    @classmethod
    def calculate_word_and_char_count(cls, text: str) -> tuple[int, int]:
        """Calculates total word count and non-whitespace character count."""
        if not text:
            return 0, 0
        # Strip code blocks and markdown markup for clean text counting
        clean = re.sub(r"```[\s\S]*?```", "", text)
        clean = re.sub(r"`[^`]*`", "", clean)
        clean = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", clean)
        clean = re.sub(r"[#*_~|]", " ", clean)

        words = [w for w in re.split(r"\s+", clean) if w]
        char_count = len(re.sub(r"\s", "", clean))
        return len(words), char_count

    @classmethod
    def estimate_read_time(cls, word_count: int, words_per_minute: int = 200) -> str:
        """Estimates reading time in minutes."""
        if word_count <= 0:
            return "< 1 min"
        minutes = math.ceil(word_count / words_per_minute)
        if minutes <= 1:
            return "1 min"
        return f"{minutes} min"

    @classmethod
    def extract_tags(cls, markdown: str, max_tags: int = 5) -> List[str]:
        """
        Extracts relevant keyword tags using technical vocabulary detection
        and high-frequency term analysis.
        """
        if not markdown:
            return []

        tags: List[str] = []

        # 1. Detect code block languages (e.g. ```python)
        code_langs = re.findall(r"```([a-zA-Z0-9_-]+)", markdown)
        for lang in code_langs:
            clean_lang = lang.capitalize()
            if clean_lang not in tags:
                tags.append(clean_lang)

        # 2. Match known high-value tech/domain keywords
        lower_md = markdown.lower()
        for kw in TECH_KEYWORDS:
            if kw in lower_md and kw.capitalize() not in tags:
                tags.append(kw.capitalize())
            if len(tags) >= max_tags:
                break

        # 3. Frequency analysis on remaining terms
        words = re.findall(r"\b[A-Za-z]{3,}\b", markdown)
        filtered = [
            w.capitalize() for w in words
            if w.lower() not in STOPWORDS and len(w) >= 4
        ]
        counts = Counter(filtered)
        for word, count in counts.most_common(max_tags * 2):
            if count >= 2 and word not in tags:
                tags.append(word)
            if len(tags) >= max_tags:
                break

        return tags[:max_tags]

    @classmethod
    def extract_document_title(cls, markdown: str) -> str:
        """Extracts top level title from markdown or returns default."""
        m = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
        if m:
            return m.group(1).strip()
        return "Document"

    @classmethod
    def generate_frontmatter(
        cls,
        title: str,
        tags: List[str],
        word_count: int,
        estimated_read_time: str,
        extra_fields: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generates standard YAML frontmatter block."""
        tags_str = "[" + ", ".join(f'"{t}"' for t in tags) + "]"
        lines = [
            "---",
            f'title: "{title}"',
            f"tags: {tags_str}",
            f"word_count: {word_count}",
            f'estimated_read_time: "{estimated_read_time}"',
        ]
        if extra_fields:
            for k, v in extra_fields.items():
                if isinstance(v, str):
                    lines.append(f'{k}: "{v}"')
                elif isinstance(v, (int, float, bool)):
                    lines.append(f"{k}: {v}")
                elif isinstance(v, list):
                    items = ", ".join(f'"{x}"' if isinstance(x, str) else str(x) for x in v)
                    lines.append(f"{k}: [{items}]")
        lines.append("---")
        return "\n".join(lines)

    @classmethod
    def inject_frontmatter(cls, markdown: str, frontmatter: str) -> str:
        """Prepends frontmatter to document, replacing existing if present."""
        if not frontmatter:
            return markdown
        # If document already has frontmatter, replace it
        if re.match(r"^---\n[\s\S]*?\n---\n*", markdown):
            return re.sub(r"^---\n[\s\S]*?\n---\n*", f"{frontmatter}\n\n", markdown)
        return f"{frontmatter}\n\n{markdown.lstrip()}"
