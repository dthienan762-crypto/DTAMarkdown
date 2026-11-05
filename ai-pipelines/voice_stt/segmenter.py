"""
DTAMarkdown Studio - Voice STT Segmenter & Timestamp Formatter
Handles silence-gap paragraph segmentation, punctuation normalization,
and Markdown bold timestamp header formatting (**[HH:MM:SS]**).
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List


@dataclass
class AudioSegment:
    """Represents a speech segment with start/end timestamps and recognized text."""
    start: float  # in seconds
    end: float    # in seconds
    text: str


def format_timestamp(seconds: float) -> str:
    """
    Converts floating-point seconds into standardized **[HH:MM:SS]** string.
    Example: 0.0 -> '00:00:00', 75.5 -> '00:01:15', 3661.0 -> '01:01:01'.
    """
    total_seconds = max(0, int(seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def normalize_punctuation(text: str) -> str:
    """
    Ensures sentence capitalization, spacing around punctuation,
    and trailing period if missing.
    """
    if not text:
        return ""

    s = text.strip()
    if not s:
        return ""

    # Collapse multiple whitespaces
    s = re.sub(r"\s+", " ", s)

    # Capitalize first letter
    s = s[0].upper() + s[1:]

    # Capitalize letter following sentence-ending punctuation (. ? !)
    def cap_after_punct(m: re.Match) -> str:
        punct = m.group(1)
        char = m.group(2).upper()
        return f"{punct} {char}"

    s = re.sub(r"([.?!])\s+([a-z])", cap_after_punct, s)

    # Add trailing period if missing punctuation
    if not s.endswith((".", "!", "?", ":", ";")):
        s += "."

    return s


class AudioSegmenter:
    """
    Segments speech streams into structured Markdown paragraphs
    using configurable silence pause thresholds.
    """

    @classmethod
    def format_segments_to_markdown(
        cls,
        segments: List[AudioSegment],
        silence_threshold: float = 2.0,
        title: str = "Audio Transcript"
    ) -> str:
        """
        Formats a list of AudioSegments into clean Markdown with timestamps:
        ## Audio Transcript

        **[00:00:00]** First paragraph text...

        **[00:00:15]** Second paragraph text after a pause...
        """
        if not segments:
            return f"## {title}\n\n*No speech detected.*"

        md_lines = [f"## {title}", ""]
        current_para_texts: List[str] = []
        para_start_time = 0.0
        prev_end = 0.0

        for seg in segments:
            clean_text = seg.text.strip()
            if not clean_text:
                continue

            # Check if silence gap between segments exceeds threshold
            is_new_paragraph = (seg.start - prev_end > silence_threshold) and bool(current_para_texts)

            if is_new_paragraph:
                # Flush previous paragraph
                para_body = " ".join(current_para_texts)
                para_body = normalize_punctuation(para_body)
                ts_str = format_timestamp(para_start_time)
                md_lines.append(f"**[{ts_str}]** {para_body}")
                md_lines.append("")

                current_para_texts = []
                para_start_time = seg.start
            elif not current_para_texts:
                para_start_time = seg.start

            current_para_texts.append(clean_text)
            prev_end = seg.end

        # Flush final accumulated paragraph
        if current_para_texts:
            para_body = " ".join(current_para_texts)
            para_body = normalize_punctuation(para_body)
            ts_str = format_timestamp(para_start_time)
            md_lines.append(f"**[{ts_str}]** {para_body}")

        return "\n".join(md_lines).strip() + "\n"
