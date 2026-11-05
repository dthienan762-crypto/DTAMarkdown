"""
Unit tests for Voice STT Pipeline (/ai-pipelines/voice_stt/)
Verifies WAV ingestion without ffmpeg, silence-gap paragraph segmentation,
timestamp formatting (**[HH:MM:SS]**), punctuation normalization, and boundary handling.
"""

import math
from pathlib import Path
import struct
import sys
import tempfile
import wave
import pytest

PIPELINES_DIR = Path(__file__).resolve().parent.parent
if str(PIPELINES_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINES_DIR))

from schemas import ConversionOptions, EmptyFileError, PipelineError, PipelineType
from voice_stt.segmenter import AudioSegment, AudioSegmenter, format_timestamp, normalize_punctuation
from voice_stt.stt_engine import VoiceSTTEngine


def test_timestamp_formatting():
    assert format_timestamp(0.0) == "00:00:00"
    assert format_timestamp(45.0) == "00:00:45"
    assert format_timestamp(75.5) == "00:01:15"
    assert format_timestamp(3665.0) == "01:01:05"


def test_punctuation_normalization():
    raw = "hello and welcome to the presentation this is great"
    norm = normalize_punctuation(raw)
    assert norm.startswith("Hello")
    assert norm.endswith(".")

    multi = "first sentence. second sentence? third sentence"
    norm_multi = normalize_punctuation(multi)
    assert "First sentence. Second sentence? Third sentence." == norm_multi


def test_audio_segmenter_silence_gap():
    # Gap between seg1 and seg2 is 0.5s (<= 2.0s -> same paragraph)
    # Gap between seg2 and seg3 is 4.0s (> 2.0s -> new paragraph)
    segments = [
        AudioSegment(start=0.0, end=2.0, text="Welcome everyone to the demo."),
        AudioSegment(start=2.5, end=4.0, text="Today we are discussing AI pipelines."),
        AudioSegment(start=8.0, end=10.0, text="Moving on to the next chapter."),
    ]

    md = AudioSegmenter.format_segments_to_markdown(segments, silence_threshold=2.0)

    assert "## Audio Transcript" in md
    assert "**[00:00:00]** Welcome everyone to the demo. Today we are discussing AI pipelines." in md
    assert "**[00:00:08]** Moving on to the next chapter." in md


def test_stt_engine_wav_signal_analysis():
    engine = VoiceSTTEngine()

    # 1. Pure silence 1-second WAV
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        silent_wav = Path(tf.name)

    with wave.open(str(silent_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(struct.pack("<h", 0) * 16000)

    try:
        duration, rms, is_silent = engine.analyze_wav_signal(silent_wav)
        assert duration == 1.0
        assert rms == 0.0
        assert is_silent is True

        # Test convert on silent WAV
        options = ConversionOptions(generate_toc=False, extract_tags=False)
        result = engine.convert(silent_wav, options)
        assert result.success is True
        assert "No speech detected." in result.markdown
        assert result.metadata.get("status") == "NO_SPEECH_DETECTED"
    finally:
        if silent_wav.exists():
            silent_wav.unlink()

    # 2. Synthetic Audio tone (non-silent)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        tone_wav = Path(tf.name)

    with wave.open(str(tone_wav), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        # 440 Hz tone
        samples = [int(8000 * math.sin(2 * math.pi * 440 * i / 16000)) for i in range(16000)]
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    try:
        duration, rms, is_silent = engine.analyze_wav_signal(tone_wav)
        assert duration == 1.0
        assert rms > 5000.0
        assert is_silent is False

        options = ConversionOptions(generate_toc=False, extract_tags=False)
        result = engine.convert(tone_wav, options)
        assert result.success is True
        assert result.pipeline == PipelineType.VOICE_STT
        assert "Audio Transcript" in result.markdown
    finally:
        if tone_wav.exists():
            tone_wav.unlink()


def test_stt_engine_empty_and_corrupt_boundaries():
    engine = VoiceSTTEngine()
    options = ConversionOptions()

    # 1. 0-byte file boundary
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        empty_wav = Path(tf.name)
    try:
        with pytest.raises(EmptyFileError):
            engine.convert(empty_wav, options)
    finally:
        if empty_wav.exists():
            empty_wav.unlink()

    # 2. Corrupt WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        corrupt_wav = Path(tf.name)
        corrupt_wav.write_bytes(b"NOT_A_VALID_RIFF_HEADER")
    try:
        with pytest.raises(PipelineError):
            engine.convert(corrupt_wav, options)
    finally:
        if corrupt_wav.exists():
            corrupt_wav.unlink()
