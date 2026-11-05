"""
DTAMarkdown Studio - Multimodal AI Pipelines Package
Production package exporting schemas, engines, and unified async runners.
Supports both direct imports and package-level relative imports.
"""

import sys
from pathlib import Path

# Ensure directory is on sys.path for direct module resolution
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from .schemas import (
        ConversionMetadata,
        ConversionOptions,
        ConversionResult,
        DegradedInputError,
        EmptyFileError,
        JobStatus,
        PipelineError,
        PipelineResult,
        PipelineType,
        PreferredEngine,
        StreamChunk,
        UnsupportedFormatError,
    )
    from .pipeline_runner import (
        PipelineRunner,
        detect_pipeline_type,
        run_pipeline,
        stream_pipeline,
    )
    from .text_engine import (
        MathShield,
        TableNormalizer,
        TagExtractor,
        TextNormalizer,
        TOCGenerator,
        generate_github_slug,
    )
    from .vision_ocr import (
        MathExtractor,
        PostProcessorValidator,
        TableExtractor,
        VisionOCREngine,
    )
    from .voice_stt import (
        AudioSegment,
        AudioSegmenter,
        VoiceSTTEngine,
        format_timestamp,
        normalize_punctuation,
    )
except (ImportError, ValueError):
    from schemas import (
        ConversionMetadata,
        ConversionOptions,
        ConversionResult,
        DegradedInputError,
        EmptyFileError,
        JobStatus,
        PipelineError,
        PipelineResult,
        PipelineType,
        PreferredEngine,
        StreamChunk,
        UnsupportedFormatError,
    )
    from pipeline_runner import (
        PipelineRunner,
        detect_pipeline_type,
        run_pipeline,
        stream_pipeline,
    )
    from text_engine import (
        MathShield,
        TableNormalizer,
        TagExtractor,
        TextNormalizer,
        TOCGenerator,
        generate_github_slug,
    )
    from vision_ocr import (
        MathExtractor,
        PostProcessorValidator,
        TableExtractor,
        VisionOCREngine,
    )
    from voice_stt import (
        AudioSegment,
        AudioSegmenter,
        VoiceSTTEngine,
        format_timestamp,
        normalize_punctuation,
    )

__all__ = [
    # Schemas & Enums
    "PipelineType",
    "JobStatus",
    "PreferredEngine",
    "ConversionOptions",
    "ConversionMetadata",
    "ConversionResult",
    "PipelineResult",
    "StreamChunk",
    # Exceptions
    "PipelineError",
    "DegradedInputError",
    "UnsupportedFormatError",
    "EmptyFileError",
    # Runner
    "PipelineRunner",
    "detect_pipeline_type",
    "run_pipeline",
    "stream_pipeline",
    # Text Engine
    "MathShield",
    "TableNormalizer",
    "TextNormalizer",
    "TOCGenerator",
    "generate_github_slug",
    "TagExtractor",
    # Vision OCR
    "TableExtractor",
    "MathExtractor",
    "PostProcessorValidator",
    "VisionOCREngine",
    # Voice STT
    "AudioSegment",
    "AudioSegmenter",
    "VoiceSTTEngine",
    "format_timestamp",
    "normalize_punctuation",
]
