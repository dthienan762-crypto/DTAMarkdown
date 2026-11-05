import React, { useEffect, useRef } from 'react';
import { Square, X, Mic } from 'lucide-react';

interface WaveformVisualizerProps {
  analyserNode: AnalyserNode | null;
  durationSeconds: number;
  onStop: () => void;
  onCancel: () => void;
}

export const WaveformVisualizer: React.FC<WaveformVisualizerProps> = ({
  analyserNode,
  durationSeconds,
  onStop,
  onCancel,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationFrameIdRef = useRef<number | null>(null);

  const formatDuration = (totalSeconds: number) => {
    const mins = Math.floor(totalSeconds / 60);
    const secs = totalSeconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let phase = 0;

    const render = () => {
      const width = canvas.width;
      const height = canvas.height;

      // Clear with dark surface background
      ctx.fillStyle = '#0f172a'; // slate-900
      ctx.fillRect(0, 0, width, height);

      // Draw subtle grid lines
      ctx.strokeStyle = '#1e293b'; // slate-800
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, height / 2);
      ctx.lineTo(width, height / 2);
      ctx.stroke();

      if (analyserNode) {
        const bufferLength = analyserNode.frequencyBinCount;
        const timeData = new Uint8Array(bufferLength);
        const freqData = new Uint8Array(bufferLength);

        analyserNode.getByteTimeDomainData(timeData);
        analyserNode.getByteFrequencyData(freqData);

        // Calculate average volume to scale waveform amplitude
        let sum = 0;
        for (let i = 0; i < bufferLength; i++) {
          sum += Math.abs(timeData[i] - 128);
        }
        const volume = sum / bufferLength; // 0 to 128

        // Draw dynamic frequency bars behind waveform
        const barWidth = (width / 64) * 0.8;
        const barStep = width / 64;
        for (let i = 0; i < 64; i++) {
          const freqIndex = Math.floor((i / 64) * (bufferLength / 4));
          const val = freqData[freqIndex] || 0;
          const barHeight = (val / 255) * (height * 0.7);

          const barGrad = ctx.createLinearGradient(0, height / 2 - barHeight / 2, 0, height / 2 + barHeight / 2);
          barGrad.addColorStop(0, 'rgba(129, 140, 248, 0.4)'); // indigo-400
          barGrad.addColorStop(1, 'rgba(192, 132, 252, 0.1)'); // purple-400

          ctx.fillStyle = barGrad;
          ctx.fillRect(i * barStep + 4, height / 2 - barHeight / 2, barWidth, barHeight);
        }

        // Draw sine-wave ribbon with linear gradient (#818cf8 to #c084fc)
        const gradient = ctx.createLinearGradient(0, 0, width, 0);
        gradient.addColorStop(0, '#818cf8'); // indigo-400
        gradient.addColorStop(0.5, '#a855f7'); // purple-500
        gradient.addColorStop(1, '#c084fc'); // purple-400

        ctx.lineWidth = 2.5;
        ctx.strokeStyle = gradient;
        ctx.beginPath();

        const sliceWidth = width / bufferLength;
        let x = 0;

        for (let i = 0; i < bufferLength; i++) {
          const v = timeData[i] / 128.0; // 0.0 to 2.0
          const y = (v * height) / 2;

          if (i === 0) {
            ctx.moveTo(x, y);
          } else {
            ctx.lineTo(x, y);
          }

          x += sliceWidth;
        }

        ctx.lineTo(width, height / 2);
        ctx.stroke();

        // Second subtle harmonic wave for richness
        ctx.lineWidth = 1.2;
        ctx.strokeStyle = 'rgba(192, 132, 252, 0.45)';
        ctx.beginPath();
        x = 0;
        phase += 0.05 + volume * 0.005;

        for (let i = 0; i < width; i += 4) {
          const wave = Math.sin((i / width) * 12 + phase) * (8 + volume * 1.2);
          const y = height / 2 + wave;
          if (i === 0) ctx.moveTo(i, y);
          else ctx.lineTo(i, y);
        }
        ctx.stroke();
      } else {
        // Idle calming sine wave
        phase += 0.03;
        ctx.lineWidth = 2;
        ctx.strokeStyle = 'rgba(129, 140, 248, 0.4)';
        ctx.beginPath();
        for (let x = 0; x < width; x += 3) {
          const y = height / 2 + Math.sin(x * 0.02 + phase) * 6;
          if (x === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.stroke();
      }

      animationFrameIdRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      if (animationFrameIdRef.current) {
        cancelAnimationFrame(animationFrameIdRef.current);
      }
    };
  }, [analyserNode]);

  return (
    <div className="w-full bg-slate-900 border border-indigo-500/40 rounded-xl p-4 shadow-lg shadow-indigo-500/10 transition-all duration-300">
      <div className="flex items-center justify-between mb-3">
        {/* Pulsing Recording Indicator */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-rose-950/80 border border-rose-800/80 px-3 py-1 rounded-full">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500"></span>
            </span>
            <span className="font-mono text-xs font-semibold text-rose-300 tracking-wider">
              REC {formatDuration(durationSeconds)}
            </span>
          </div>
          <span className="text-xs text-slate-400 hidden sm:inline-flex items-center gap-1.5">
            <Mic className="w-3.5 h-3.5 text-indigo-400" />
            16-bit 16kHz PCM WAV Recording
          </span>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
            title="Discard audio recording"
          >
            <X className="w-3.5 h-3.5" />
            Cancel
          </button>
          <button
            type="button"
            onClick={onStop}
            className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow shadow-indigo-500/25 transition-all"
            title="Finish recording and convert"
          >
            <Square className="w-3.5 h-3.5 fill-current" />
            Stop & Convert
          </button>
        </div>
      </div>

      {/* Real-time 60 FPS Canvas */}
      <div className="relative rounded-lg overflow-hidden border border-slate-800">
        <canvas
          ref={canvasRef}
          width={800}
          height={68}
          className="w-full h-16 block bg-slate-900"
        />
      </div>
    </div>
  );
};
