import { useState, useRef, useCallback } from 'react';
import { encodeWAV } from '../lib/wavEncoder';

export interface AudioRecorderState {
  isRecording: boolean;
  durationSeconds: number;
  analyserNode: AnalyserNode | null;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<Blob | null>;
  cancelRecording: () => void;
  error: string | null;
}

export function useAudioRecorder(): AudioRecorderState {
  const [isRecording, setIsRecording] = useState(false);
  const [durationSeconds, setDurationSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [analyserNode, setAnalyserNode] = useState<AnalyserNode | null>(null);

  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const audioChunksRef = useRef<Float32Array[]>([]);
  const timerIntervalRef = useRef<number | null>(null);
  const sourceSampleRateRef = useRef<number>(44100);

  const cleanup = useCallback(() => {
    if (timerIntervalRef.current) {
      clearInterval(timerIntervalRef.current);
      timerIntervalRef.current = null;
    }
    if (scriptProcessorRef.current) {
      scriptProcessorRef.current.disconnect();
      scriptProcessorRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    setAnalyserNode(null);
    setIsRecording(false);
    setDurationSeconds(0);
  }, []);

  const startRecording = useCallback(async () => {
    try {
      setError(null);
      audioChunksRef.current = [];

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      mediaStreamRef.current = stream;

      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AudioCtx();
      audioContextRef.current = ctx;
      sourceSampleRateRef.current = ctx.sampleRate;

      // Resume context if suspended (browser autoplay policy)
      if (ctx.state === 'suspended') {
        await ctx.resume();
      }

      const source = ctx.createMediaStreamSource(stream);

      // Create AnalyserNode for 60 FPS real-time waveform visualization
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      analyser.smoothingTimeConstant = 0.8;
      source.connect(analyser);
      setAnalyserNode(analyser);

      // Create ScriptProcessor for capturing raw PCM chunks
      const bufferSize = 4096;
      const processor = ctx.createScriptProcessor(bufferSize, 1, 1);
      scriptProcessorRef.current = processor;

      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        // Copy chunk
        const chunk = new Float32Array(inputData.length);
        chunk.set(inputData);
        audioChunksRef.current.push(chunk);
      };

      source.connect(processor);

      // Create a silent gain node to prevent speaker feedback while keeping the processor alive
      const silentGain = ctx.createGain();
      silentGain.gain.value = 0;
      processor.connect(silentGain);
      silentGain.connect(ctx.destination);

      setIsRecording(true);
      setDurationSeconds(0);

      const startTime = Date.now();
      timerIntervalRef.current = window.setInterval(() => {
        setDurationSeconds(Math.floor((Date.now() - startTime) / 1000));
      }, 500);
    } catch (err: unknown) {
      cleanup();
      const message = err instanceof Error ? err.message : 'Microphone access denied or unavailable';
      setError(message);
      throw err;
    }
  }, [cleanup]);

  const stopRecording = useCallback(async (): Promise<Blob | null> => {
    if (!isRecording) return null;

    // Collect all samples
    const chunks = audioChunksRef.current;
    const sampleRate = sourceSampleRateRef.current;

    cleanup();

    if (chunks.length === 0) {
      return null;
    }

    // Flatten all chunks into a single Float32Array
    const totalLength = chunks.reduce((acc, chunk) => acc + chunk.length, 0);
    const merged = new Float32Array(totalLength);
    let offset = 0;
    for (const chunk of chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    // Encode to 16-bit PCM WAV (16kHz mono)
    const wavBlob = encodeWAV(merged, sampleRate, 16000);
    return wavBlob;
  }, [isRecording, cleanup]);

  const cancelRecording = useCallback(() => {
    audioChunksRef.current = [];
    cleanup();
  }, [cleanup]);

  return {
    isRecording,
    durationSeconds,
    analyserNode,
    startRecording,
    stopRecording,
    cancelRecording,
    error,
  };
}
