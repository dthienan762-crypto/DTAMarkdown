import { describe, it, expect } from 'vitest';
import { encodeWAV, resampleAudio } from '../lib/wavEncoder';

describe('wavEncoder', () => {
  it('resamples audio buffer accurately using linear interpolation', () => {
    // 48000 Hz buffer with 4800 samples = 100ms
    const sourceRate = 48000;
    const targetRate = 16000;
    const originalLength = 4800;
    const source = new Float32Array(originalLength);

    for (let i = 0; i < originalLength; i++) {
      source[i] = Math.sin((i / originalLength) * 2 * Math.PI);
    }

    const resampled = resampleAudio(source, sourceRate, targetRate);
    expect(resampled.length).toBe(1600); // exactly 1/3 of original length

    // Check bounds
    for (let i = 0; i < resampled.length; i++) {
      expect(resampled[i]).toBeGreaterThanOrEqual(-1);
      expect(resampled[i]).toBeLessThanOrEqual(1);
      expect(Number.isNaN(resampled[i])).toBe(false);
    }
  });

  it('preserves buffer when source and target rates match', () => {
    const source = new Float32Array([0.1, 0.5, -0.5, 0.0]);
    const resampled = resampleAudio(source, 16000, 16000);
    expect(resampled).toBe(source);
  });

  it('encodes Float32 samples into canonical 16-bit PCM WAV', async () => {
    const sampleRate = 48000;
    const targetRate = 16000;
    const durationSec = 0.5;
    const sampleCount = Math.floor(sampleRate * durationSec);
    const samples = new Float32Array(sampleCount);

    for (let i = 0; i < sampleCount; i++) {
      samples[i] = 0.5 * Math.sin((2 * Math.PI * 440 * i) / sampleRate);
    }

    const blob = encodeWAV(samples, sampleRate, targetRate);
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toBe('audio/wav');

    const expectedSampleCount = Math.round(sampleCount / (sampleRate / targetRate));
    const expectedByteLength = 44 + expectedSampleCount * 2;
    expect(blob.size).toBe(expectedByteLength);

    // Verify RIFF WAVE header bytes
    const arrayBuffer = await blob.arrayBuffer();
    const view = new DataView(arrayBuffer);

    // Helper to read string from DataView
    const readString = (offset: number, length: number) => {
      let s = '';
      for (let i = 0; i < length; i++) {
        s += String.fromCharCode(view.getUint8(offset + i));
      }
      return s;
    };

    expect(readString(0, 4)).toBe('RIFF');
    expect(view.getUint32(4, true)).toBe(36 + expectedSampleCount * 2);
    expect(readString(8, 4)).toBe('WAVE');
    expect(readString(12, 4)).toBe('fmt ');
    expect(view.getUint32(16, true)).toBe(16); // Subchunk1Size
    expect(view.getUint16(20, true)).toBe(1); // AudioFormat: 1 (PCM)
    expect(view.getUint16(22, true)).toBe(1); // NumChannels: 1 (mono)
    expect(view.getUint32(24, true)).toBe(16000); // SampleRate: 16000 Hz
    expect(view.getUint32(28, true)).toBe(32000); // ByteRate: 16000 * 1 * 2 = 32000
    expect(view.getUint16(32, true)).toBe(2); // BlockAlign: 1 * 2 = 2
    expect(view.getUint16(34, true)).toBe(16); // BitsPerSample: 16-bit
    expect(readString(36, 4)).toBe('data');
    expect(view.getUint32(40, true)).toBe(expectedSampleCount * 2);
  });

  it('clamps extreme out-of-range float values without wrapping or overflow', async () => {
    const samples = new Float32Array([2.5, -3.0, 1.0, -1.0]);
    const blob = encodeWAV(samples, 16000, 16000);
    const arrayBuffer = await blob.arrayBuffer();
    const view = new DataView(arrayBuffer);

    // Offset 44 starts the 16-bit PCM data
    const sample0 = view.getInt16(44, true);
    const sample1 = view.getInt16(46, true);
    const sample2 = view.getInt16(48, true);
    const sample3 = view.getInt16(50, true);

    expect(sample0).toBe(32767); // Clamped max
    expect(sample1).toBe(-32768); // Clamped min
    expect(sample2).toBe(32767);
    expect(sample3).toBe(-32768);
  });
});
