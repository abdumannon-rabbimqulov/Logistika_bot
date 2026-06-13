/**
 * VoiceRecorder — Telegram-style inline recording UI
 *
 * Features:
 *  • Animated waveform bars (canvas + CSS fallback)
 *  • Slide-to-cancel indicator
 *  • Duration display with pulse dot
 *  • Proper lifecycle tied to useVoiceRecorder hook
 */
import React, { useRef, useEffect, useCallback } from "react";
import { Trash2, Send, ChevronLeft } from "lucide-react";
import { useVoiceRecorder } from "../../hooks/useVoiceRecorder";

interface VoiceRecorderProps {
  chatId: number;
  onSend: (file: File) => void;
  onCancel: () => void;
  /** If true, the component is in hold-to-record mode (auto-send on release) */
  holdMode?: boolean;
  /** Horizontal drag distance (px) from the mic button — for slide-to-cancel */
  slideOffset?: number;
}

/** How far left the user must drag (px) to trigger cancel */
const CANCEL_THRESHOLD = 100;

export const VoiceRecorder: React.FC<VoiceRecorderProps> = ({
  chatId,
  onSend,
  onCancel,
  holdMode = false,
  slideOffset = 0,
}) => {
  const {
    state,
    duration,
    error,
    analyserNode,
    startRecording,
    stopRecording,
    cancelRecording,
  } = useVoiceRecorder();

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number | null>(null);
  const didStartRef = useRef(false);

  /* ── Auto-start on mount ──────────────────────────────────── */
  useEffect(() => {
    if (!didStartRef.current) {
      didStartRef.current = true;
      startRecording().then((ok) => {
        if (!ok) onCancel();
      });
    }
    return () => {
      cancelRecording();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Hold-release event (from parent gesture handler) ──── */
  useEffect(() => {
    if (!holdMode) return;
    const onRelease = async () => {
      const file = await stopRecording();
      if (file) {
        onSend(file);
      } else {
        onCancel();
      }
    };
    window.addEventListener("voice:hold-release", onRelease);
    return () => window.removeEventListener("voice:hold-release", onRelease);
  }, [holdMode, stopRecording, onSend, onCancel]);

  /* ── Error → cancel ───────────────────────────────────────── */
  useEffect(() => {
    if (error) {
      alert(error);
      onCancel();
    }
  }, [error, onCancel]);

  /* ── Waveform visualizer ──────────────────────────────────── */
  useEffect(() => {
    if (!analyserNode || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const bufLen = analyserNode.frequencyBinCount;
    const dataArr = new Uint8Array(bufLen);

    const draw = () => {
      animFrameRef.current = requestAnimationFrame(draw);
      analyserNode.getByteFrequencyData(dataArr);

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Draw bar-style waveform
      const barCount = 32;
      const step = Math.floor(bufLen / barCount);
      const barW = canvas.width / barCount - 1;
      const midY = canvas.height / 2;

      for (let i = 0; i < barCount; i++) {
        const v = dataArr[i * step] / 255;
        const barH = Math.max(2, v * midY);

        // Neon gradient: cyan → blue
        const hue = 190 + (i / barCount) * 30;
        ctx.fillStyle = `hsla(${hue}, 100%, 60%, 0.9)`;
        ctx.fillRect(
          i * (barW + 1),
          midY - barH,
          barW,
          barH * 2
        );
      }
    };
    draw();

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [analyserNode]);

  /* ── Slide-to-cancel detection ────────────────────────────── */
  const isCancelling = slideOffset < -CANCEL_THRESHOLD;

  useEffect(() => {
    if (isCancelling && state === "recording") {
      cancelRecording();
      onCancel();
    }
  }, [isCancelling, state, cancelRecording, onCancel]);

  /* ── Actions ──────────────────────────────────────────────── */
  const handleStopAndSend = useCallback(async () => {
    const file = await stopRecording();
    if (file) {
      onSend(file);
    } else {
      onCancel();
    }
  }, [stopRecording, onSend, onCancel]);

  const handleCancel = useCallback(() => {
    cancelRecording();
    onCancel();
  }, [cancelRecording, onCancel]);

  /* ── Format ───────────────────────────────────────────────── */
  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = (secs % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  /* ── Render ───────────────────────────────────────────────── */
  if (state === "requesting") {
    return (
      <div className="tg-voice-recorder">
        <div className="tg-voice-recorder-inner tg-voice-requesting">
          <div className="tg-voice-spinner" />
          <span className="tg-voice-time">Mikrofon...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="tg-voice-recorder">
      <div className="tg-voice-recorder-inner">
        {/* Pulse dot */}
        <div className="tg-voice-pulse-dot" />

        {/* Duration */}
        <span className="tg-voice-time">{formatTime(duration)}</span>

        {/* Waveform canvas */}
        <canvas
          ref={canvasRef}
          className="tg-voice-canvas"
          width={128}
          height={32}
        />

        {/* Slide hint (only in hold mode) */}
        {holdMode && (
          <div
            className="tg-voice-slide-hint"
            style={{
              opacity: Math.max(0, 1 - Math.abs(slideOffset) / CANCEL_THRESHOLD),
            }}
          >
            <ChevronLeft size={14} />
            <span>Bekor qilish</span>
          </div>
        )}

        {/* Cancel button (tap mode only) */}
        {!holdMode && (
          <button
            type="button"
            className="tg-voice-cancel-btn"
            onClick={handleCancel}
            aria-label="Bekor qilish"
          >
            <Trash2 size={18} />
          </button>
        )}

        {/* Send button (tap mode only) */}
        {!holdMode && (
          <button
            type="button"
            className="tg-voice-send-btn"
            onClick={handleStopAndSend}
            aria-label="Yuborish"
          >
            <Send size={18} />
          </button>
        )}
      </div>
    </div>
  );
};
