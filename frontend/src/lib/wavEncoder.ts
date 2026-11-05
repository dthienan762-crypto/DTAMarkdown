/**
 * Browser-native 16-bit PCM WAV Encoder (16kHz mono).
 * Generates standard RIFF WAVE files that can be directly ingested
 * by Python's `wave` module and `SpeechRecognition` without requiring ffmpeg.
 */

export interface WavEncodingOptions {
  sampleRate?: number; // target sample rate, defaults to 16000 Hz
  numChannels?: number; // target channels, defaults to 1 (mono)
}

/**
 * Resamples Float32 audio buffer from source sample rate to target sample rate using linear interpolation.
 */
export function resampleAudio(
  sourceBuffer: Float32Array,
  sourceRate: number,
  targetRate: number
): Float32Array {
  if (sourceRate === targetRate) {
    return sourceBuffer;
  }
  const ratio = sourceRate / targetRate;
  const newLength = Math.round(sourceBuffer.length / ratio);
  const result = new Float32Array(newLength);

  for (let i = 0; i < newLength; i++) {
    const originalPos = i * ratio;
    const index = Math.floor(originalPos);
    const fraction = originalPos - index;

    const sample1 = sourceBuffer[index] ?? 0;
    const sample2 = sourceBuffer[index + 1] ?? sample1;
    result[i] = sample1 + fraction * (sample2 - sample1);
  }

  return result;
}

/**
 * Encodes Float32 samples into a 16-bit PCM WAV Blob.
 */
export function encodeWAV(
  samples: Float32Array,
  sourceSampleRate: number,
  targetSampleRate: number = 16000
): Blob {
  // 1. Resample to target sample rate (e.g. 16kHz)
  const resampled = resampleAudio(samples, sourceSampleRate, targetSampleRate);
  const numChannels = 1;
  const bytesPerSample = 2; // 16-bit
  const blockAlign = numChannels * bytesPerSample;
  const byteRate = targetSampleRate * blockAlign;
  const dataSize = resampled.length * bytesPerSample;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  // Helper to write ASCII strings
  const writeString = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };

  /* RIFF identifier */
  writeString(0, 'RIFF');
  /* file length */
  view.setUint32(4, 36 + dataSize, true);
  /* RIFF type */
  writeString(8, 'WAVE');
  /* format chunk identifier */
  writeString(12, 'fmt ');
  /* format chunk length */
  view.setUint32(16, 16, true);
  /* sample format (raw PCM = 1) */
  view.setUint16(20, 1, true);
  /* channel count */
  view.setUint16(22, numChannels, true);
  /* sample rate */
  view.setUint32(24, targetSampleRate, true);
  /* byte rate (sample rate * block align) */
  view.setUint32(28, byteRate, true);
  /* block align (channel count * bytes per sample) */
  view.setUint16(32, blockAlign, true);
  /* bits per sample */
  view.setUint16(34, 16, true);
  /* data chunk identifier */
  writeString(36, 'data');
  /* data chunk length */
  view.setUint32(40, dataSize, true);

  // Convert Float32 [-1.0, 1.0] to signed 16-bit PCM [-32768, 32767]
  let offset = 44;
  for (let i = 0; i < resampled.length; i++) {
    let s = Math.max(-1, Math.min(1, resampled[i]));
    const intSample = s < 0 ? s * 0x8000 : s * 0x7fff;
    view.setInt16(offset, intSample, true);
    offset += 2;
  }

  return new Blob([buffer], { type: 'audio/wav' });
}
