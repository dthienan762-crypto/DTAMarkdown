"""
DTAMarkdown Studio - Voice STT Engine
Transcribes 16-bit PCM WAV audio without external ffmpeg binary dependency.
Implements silence detection, automatic punctuation, and Markdown timestamp headers.
Multi-tier fallback: Gemini Audio API -> faster-whisper / SpeechRecognition -> Acoustic VAD.
"""

from __future__ import annotations

import base64
import json
import math
import os
from pathlib import Path
import re
import struct
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple
import urllib.request
import uuid
import wave

from schemas import (
    ConversionMetadata,
    ConversionOptions,
    DegradedInputError,
    EmptyFileError,
    PipelineError,
    PipelineResult,
    PipelineType,
    StreamChunk,
    UnsupportedFormatError,
)
from text_engine import TOCGenerator, TagExtractor
from .segmenter import AudioSegment, AudioSegmenter, format_timestamp

# Check optional SpeechRecognition
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

# Check optional faster-whisper
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False


class VoiceSTTEngine:
    """
    Production Speech-to-Text Engine operating natively on 16-bit PCM WAV.
    Completely eliminates dependencies on external system ffmpeg executables.
    """

    MAX_AUDIO_SIZE = 100 * 1024 * 1024  # 100MB limit per api_contract.yaml
    SUPPORTED_WAV_EXTENSIONS = {".wav"}
    OTHER_AUDIO_EXTENSIONS = {".mp3", ".ogg", ".flac", ".m4a"}

    SYSTEM_PROMPT = (
        "You are an expert audio transcription system. Transcribe the provided audio recording "
        "into clean, properly punctuated Markdown with timestamps.\n"
        "Rules:\n"
        "1. Punctuation: Ensure natural capitalization and punctuation (. , ? !).\n"
        "2. Format: Group speech into paragraphs based on silence gaps (>2s). "
        "Prepend each paragraph with a bold timestamp in format **[HH:MM:SS]**.\n"
        "3. Preserve speaker intent accurately.\n"
        "4. Output ONLY the raw Markdown transcript. Do not wrap in outer ```markdown code blocks."
    )

    def __init__(self):
        self.whisper_model = None
        if FASTER_WHISPER_AVAILABLE:
            try:
                # Load lightweight quantized model (int8) for sub-second local transcription
                self.whisper_model = WhisperModel("tiny", device="cpu", compute_type="int8")
            except Exception:
                self.whisper_model = None

    def validate_audio_file(self, file_path: Path) -> Tuple[str, int]:
        """
        Validates file existence, 0-byte boundary, 100MB size limit, and audio format.
        """
        if not file_path.exists():
            raise PipelineError(f"Audio file not found: {file_path}", code="FILE_NOT_FOUND")

        size = file_path.stat().st_size
        if size == 0:
            raise EmptyFileError(f"Uploaded audio file contains 0 bytes: {file_path.name}")

        if size > self.MAX_AUDIO_SIZE:
            raise PipelineError(
                f"Payload too large: audio size ({size} bytes) exceeds 100MB limit.",
                code="PAYLOAD_TOO_LARGE"
            )

        suffix = file_path.suffix.lower()
        if suffix in self.SUPPORTED_WAV_EXTENSIONS:
            return "wav", size
        elif suffix in self.OTHER_AUDIO_EXTENSIONS:
            return "other_audio", size
        else:
            raise UnsupportedFormatError(
                f"Unsupported audio format: '{suffix}'. Expected 16-bit PCM WAV."
            )

    def analyze_wav_signal(self, file_path: Path) -> Tuple[float, float, bool]:
        """
        Inspects WAV header and computes audio duration and RMS signal energy using standard library 'wave'.
        Returns:
            duration: total audio duration in seconds.
            rms: Root-Mean-Square signal amplitude.
            is_silent: True if RMS < 50.0 or duration == 0.
        """
        try:
            with wave.open(str(file_path), "rb") as wf:
                channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                n_frames = wf.getnframes()

                if n_frames == 0 or framerate == 0:
                    return 0.0, 0.0, True

                duration = n_frames / float(framerate)

                # Read audio frames to compute RMS energy
                frames = wf.readframes(n_frames)
                if not frames:
                    return duration, 0.0, True

                # Compute RMS for 16-bit PCM (2 bytes per sample)
                if sampwidth == 2:
                    num_samples = len(frames) // 2
                    samples = struct.unpack(f"<{num_samples}h", frames)
                    # Average over channels if stereo
                    if channels > 1:
                        samples = samples[::channels]
                    sum_sq = sum(s * s for s in samples)
                    rms = math.sqrt(sum_sq / len(samples)) if samples else 0.0
                else:
                    # Generic byte fallback
                    sum_sq = sum((b - 128) ** 2 for b in frames)
                    rms = math.sqrt(sum_sq / len(frames)) if frames else 0.0

                is_silent = (rms < 50.0)
                return duration, rms, is_silent

        except wave.Error as e:
            raise DegradedInputError(f"Malformed or corrupt WAV file header: {e}")
        except Exception as e:
            raise DegradedInputError(f"Error reading audio stream: {e}")

    def _call_gemini_audio(self, audio_bytes: bytes, mime_type: str, api_key: str) -> str:
        """Calls Gemini Multimodal Audio API directly via REST."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": self.SYSTEM_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": base64.b64encode(audio_bytes).decode("utf-8")
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1
            }
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            clean = text.strip()
            if clean.startswith("```markdown"):
                clean = clean[len("```markdown"):].strip()
            elif clean.startswith("```"):
                clean = clean[len("```"):].strip()
            if clean.endswith("```"):
                clean = clean[:-3].strip()
            return clean

    def _transcribe_speech_recognition(self, file_path: Path) -> List[AudioSegment]:
        """Transcribes audio using SpeechRecognition library."""
        if not SPEECH_RECOGNITION_AVAILABLE:
            return []

        r = sr.Recognizer()
        segments = []
        try:
            with sr.AudioFile(str(file_path)) as source:
                audio = r.record(source)
                # Attempt recognize_google
                text = r.recognize_google(audio)
                if text:
                    duration = len(audio.frame_data) / (source.SAMPLE_RATE * source.SAMPLE_WIDTH)
                    segments.append(AudioSegment(start=0.0, end=duration, text=text))
        except sr.UnknownValueError:
            # Speech was unintelligible or silent
            pass
        except Exception:
            # Network or recognition failure
            pass

        return segments

    def _transcribe_acoustic_vad(self, file_path: Path, silence_threshold: float) -> List[AudioSegment]:
        """
        Zero-cloud acoustic Voice Activity Detector (VAD).
        Analyzes audio frame energy in 0.5s windows, detects spoken segments and silence gaps.
        """
        segments: List[AudioSegment] = []
        try:
            with wave.open(str(file_path), "rb") as wf:
                framerate = wf.getframerate()
                sampwidth = wf.getsampwidth()
                channels = wf.getnchannels()
                chunk_duration = 0.5
                chunk_frames = int(framerate * chunk_duration)

                current_start: Optional[float] = None
                current_time = 0.0

                while True:
                    data = wf.readframes(chunk_frames)
                    if not data:
                        break

                    num_samples = len(data) // sampwidth
                    if sampwidth == 2:
                        samples = struct.unpack(f"<{num_samples}h", data)
                    else:
                        samples = [(b - 128) * 256 for b in data]

                    if channels > 1:
                        samples = samples[::channels]

                    rms = math.sqrt(sum(s * s for s in samples) / len(samples)) if samples else 0.0

                    if rms >= 100.0:  # Active speech threshold
                        if current_start is None:
                            current_start = current_time
                    else:
                        if current_start is not None:
                            # Speech block ended
                            seg_duration = current_time - current_start
                            if seg_duration >= 0.5:
                                segments.append(AudioSegment(
                                    start=current_start,
                                    end=current_time,
                                    text="[Audio speech segment detected]"
                                ))
                            current_start = None

                    current_time += chunk_duration

                if current_start is not None and (current_time - current_start >= 0.5):
                    segments.append(AudioSegment(
                        start=current_start,
                        end=current_time,
                        text="[Audio speech segment detected]"
                    ))

        except Exception:
            pass

        return segments

    def convert(self, file_path: Path, options: ConversionOptions) -> PipelineResult:
        """
        Transcribes audio file into Markdown with paragraph segmentation and timestamps.
        """
        start_time = time.perf_counter()
        format_cat, file_size = self.validate_audio_file(file_path)

        warnings: List[str] = []
        engine_used = "Standard Wave STT"

        # Check WAV signal properties
        if format_cat == "wav":
            duration, rms, is_silent = self.analyze_wav_signal(file_path)
            if is_silent or duration == 0:
                # Boundary: Silent or 0-second audio
                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                return PipelineResult(
                    success=True,
                    pipeline=PipelineType.VOICE_STT,
                    markdown="## Audio Transcript\n\n*No speech detected.*",
                    metadata={
                        "word_count": 0,
                        "character_count": 0,
                        "estimated_read_time": "< 1 min",
                        "duration_ms": round(elapsed_ms, 2),
                        "audio_duration_seconds": round(duration, 2),
                        "status": "NO_SPEECH_DETECTED",
                        "engine_used": "Wave Energy Analyzer",
                        "tags": ["Audio", "Transcript"],
                        "warnings": ["Audio track contained no audible speech signal."]
                    },
                    warnings=["No speech detected in audio recording."],
                    duration_ms=round(elapsed_ms, 2),
                    job_id=str(uuid.uuid4())
                )

        # Tier 1: Gemini Audio API (if API key available or preferred)
        api_key = os.environ.get("GEMINI_API_KEY")
        if (options.preferred_engine == "gemini" or options.preferred_engine == "auto") and api_key:
            try:
                mime = "audio/wav" if format_cat == "wav" else f"audio/{file_path.suffix.lstrip('.')}"
                audio_bytes = file_path.read_bytes()
                gemini_md = self._call_gemini_audio(audio_bytes, mime, api_key)
                engine_used = "Gemini Audio Multimodal API"

                elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                w_count, c_count = TagExtractor.calculate_word_and_char_count(gemini_md)
                read_time = TagExtractor.estimate_read_time(w_count)
                tags = TagExtractor.extract_tags(gemini_md) if options.extract_tags else []

                return PipelineResult(
                    success=True,
                    pipeline=PipelineType.VOICE_STT,
                    markdown=gemini_md,
                    metadata={
                        "word_count": w_count,
                        "character_count": c_count,
                        "estimated_read_time": read_time,
                        "duration_ms": round(elapsed_ms, 2),
                        "engine_used": engine_used,
                        "tags": tags,
                        "warnings": warnings,
                    },
                    warnings=warnings,
                    duration_ms=round(elapsed_ms, 2),
                    job_id=str(uuid.uuid4())
                )
            except Exception as e:
                warnings.append(f"Gemini Audio API fallback triggered due to error: {e}")

        # Tier 2: faster-whisper or SpeechRecognition
        segments: List[AudioSegment] = []

        if self.whisper_model is not None and format_cat == "wav":
            try:
                whisper_segs, _ = self.whisper_model.transcribe(
                    str(file_path),
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=500)
                )
                for ws in whisper_segs:
                    if ws.text.strip():
                        segments.append(AudioSegment(start=ws.start, end=ws.end, text=ws.text))
                engine_used = "faster-whisper (tiny int8)"
            except Exception as e:
                warnings.append(f"faster-whisper error: {e}")

        if not segments and format_cat == "wav":
            # SpeechRecognition fallback
            sr_segs = self._transcribe_speech_recognition(file_path)
            if sr_segs:
                segments = sr_segs
                engine_used = "SpeechRecognition Google STT"

        if not segments and format_cat == "wav":
            # Acoustic VAD fallback
            vad_segs = self._transcribe_acoustic_vad(file_path, options.timestamp_silence_threshold)
            if vad_segs:
                segments = vad_segs
                engine_used = "Acoustic VAD Energy Analyzer"

        # Format segments into structured Markdown paragraphs
        threshold = options.timestamp_silence_threshold
        transcript_md = AudioSegmenter.format_segments_to_markdown(segments, silence_threshold=threshold)

        # Generate Table of Contents if requested
        if options.generate_toc:
            toc = TOCGenerator.generate_toc(transcript_md)
            if toc:
                transcript_md = TOCGenerator.inject_toc(transcript_md, toc)

        # Extract tags and frontmatter
        w_count, c_count = TagExtractor.calculate_word_and_char_count(transcript_md)
        read_time = TagExtractor.estimate_read_time(w_count)
        tags = TagExtractor.extract_tags(transcript_md) if options.extract_tags else []

        if options.extract_tags and w_count > 0:
            fm = TagExtractor.generate_frontmatter("Audio Transcript", tags, w_count, read_time)
            transcript_md = TagExtractor.inject_frontmatter(transcript_md, fm)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        metadata = {
            "word_count": w_count,
            "character_count": c_count,
            "estimated_read_time": read_time,
            "duration_ms": round(elapsed_ms, 2),
            "engine_used": engine_used,
            "tags": tags,
            "warnings": warnings,
        }

        return PipelineResult(
            success=True,
            pipeline=PipelineType.VOICE_STT,
            markdown=transcript_md,
            metadata=metadata,
            warnings=warnings,
            duration_ms=round(elapsed_ms, 2),
            job_id=str(uuid.uuid4())
        )

    async def convert_stream(
        self,
        file_path: Path,
        options: ConversionOptions,
        job_id: Optional[str] = None
    ) -> AsyncIterator[StreamChunk]:
        """
        Asynchronous streaming generator yielding audio conversion updates.
        """
        jid = job_id or str(uuid.uuid4())

        yield StreamChunk(
            event="status",
            job_id=jid,
            stage="audio_validation",
            progress=15,
            message="Validating 16-bit PCM WAV audio header..."
        )

        try:
            self.validate_audio_file(file_path)
        except Exception as e:
            code = getattr(e, "code", "AUDIO_ERROR")
            yield StreamChunk(
                event="error",
                job_id=jid,
                code=code,
                message=str(e),
                recoverable=False
            )
            return

        yield StreamChunk(
            event="status",
            job_id=jid,
            stage="stt_transcription",
            progress=50,
            message="Transcribing speech and detecting silence-gap paragraphs..."
        )

        try:
            result = self.convert(file_path, options)
        except Exception as e:
            code = getattr(e, "code", "STT_FAILED")
            yield StreamChunk(
                event="error",
                job_id=jid,
                code=code,
                message=str(e),
                recoverable=False
            )
            return

        # Stream progressive paragraphs
        paragraphs = [p + "\n\n" for p in result.markdown.split("\n\n") if p.strip()]
        for idx, para in enumerate(paragraphs):
            yield StreamChunk(
                event="chunk",
                job_id=jid,
                delta=para,
                index=idx
            )

        yield StreamChunk(
            event="complete",
            job_id=jid,
            markdown=result.markdown,
            metadata=result.metadata
        )
