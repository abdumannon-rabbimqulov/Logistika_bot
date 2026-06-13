/**
 * useVoiceRecorder — Core MediaRecorder hook with:
 *  • Smart codec detection (webm → ogg → mp4 → default)
 *  • Telegram Mini App environment detection & permission handling
 *  • Promise-based stop that guarantees blob delivery
 *  • AnalyserNode exposed for waveform visualizers
 */
import { useState, useRef, useCallback, useEffect } from "react";

export type RecorderState = "idle" | "requesting" | "recording" | "stopping";

interface UseVoiceRecorderReturn {
  state: RecorderState;
  duration: number;
  error: string | null;
  analyserNode: AnalyserNode | null;
  startRecording: () => Promise<boolean>;
  stopRecording: () => Promise<File | null>;
  cancelRecording: () => void;
}

/* ── Codec negotiation ───────────────────────────────────────────── */

interface CodecInfo {
  mimeType: string;
  ext: string;
}

const CODEC_CANDIDATES: CodecInfo[] = [
  { mimeType: "audio/webm;codecs=opus", ext: "webm" },
  { mimeType: "audio/webm", ext: "webm" },
  { mimeType: "audio/ogg;codecs=opus", ext: "ogg" },
  { mimeType: "audio/ogg", ext: "ogg" },
  { mimeType: "audio/mp4", ext: "m4a" },
];

function pickCodec(): CodecInfo {
  if (typeof MediaRecorder === "undefined") {
    return { mimeType: "", ext: "webm" };
  }
  for (const c of CODEC_CANDIDATES) {
    try {
      if (MediaRecorder.isTypeSupported(c.mimeType)) return c;
    } catch {
      /* some browsers throw instead of returning false */
    }
  }
  // Fallback: let the browser decide
  return { mimeType: "", ext: "webm" };
}

/* ── Telegram environment helpers ────────────────────────────────── */

function isTelegramWebApp(): boolean {
  return !!(window as any).Telegram?.WebApp;
}

function getTelegramPlatform(): string | null {
  return (window as any).Telegram?.WebApp?.platform ?? null;
}

/* ── Minimum recording duration (ms) ─────────────────────────────── */
const MIN_DURATION_MS = 500;

/* ═══════════════════════════════════════════════════════════════════ */

export function useVoiceRecorder(): UseVoiceRecorderReturn {
  const [state, setState] = useState<RecorderState>("idle");
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [analyserNode, setAnalyserNode] = useState<AnalyserNode | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(0);
  const codecRef = useRef<CodecInfo>(pickCodec());

  // Promise resolver for stopRecording
  const stopResolveRef = useRef<((file: File | null) => void) | null>(null);
  const isRecordingRef = useRef(false);

  /* ── Cleanup on unmount ──────────────────────────────────────── */
  useEffect(() => {
    return () => {
      // eslint-disable-next-line react-hooks/exhaustive-deps
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const cleanup = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.stop();
      } catch { /* already stopped */ }
    }
    mediaRecorderRef.current = null;

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (audioCtxRef.current) {
      try { audioCtxRef.current.close(); } catch { /* */ }
      audioCtxRef.current = null;
    }
    setAnalyserNode(null);
    isRecordingRef.current = false;
  }, []);

  /* ── Start ───────────────────────────────────────────────────── */
  const startRecording = useCallback(async (): Promise<boolean> => {
    setError(null);

    if (typeof MediaRecorder === "undefined") {
      setError("Bu brauzerda ovoz yozish qo'llab-quvvatlanmaydi.");
      return false;
    }

    setState("requesting");

    // Telegram-specific guidance
    const tgPlatform = getTelegramPlatform();
    const inTelegram = isTelegramWebApp();

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      streamRef.current = stream;

      // Re-pick codec (in case browser context changed, e.g. Telegram iframe)
      codecRef.current = pickCodec();
      const codec = codecRef.current;

      const options: MediaRecorderOptions = {};
      if (codec.mimeType) {
        options.mimeType = codec.mimeType;
      }

      const recorder = new MediaRecorder(stream, options);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = () => {
        const chunks = chunksRef.current;
        if (stopResolveRef.current) {
          if (chunks.length > 0) {
            const actualMime = codec.mimeType || recorder.mimeType || "audio/webm";
            const blob = new Blob(chunks, { type: actualMime });
            const file = new File(
              [blob],
              `voice_${Date.now()}.${codec.ext}`,
              { type: actualMime }
            );
            stopResolveRef.current(file);
          } else {
            stopResolveRef.current(null);
          }
          stopResolveRef.current = null;
        }
        cleanup();
        setState("idle");
        setDuration(0);
      };

      recorder.onerror = () => {
        setError("Ovoz yozishda xatolik yuz berdi.");
        if (stopResolveRef.current) {
          stopResolveRef.current(null);
          stopResolveRef.current = null;
        }
        cleanup();
        setState("idle");
        setDuration(0);
      };

      // Request data every 250ms for smoother stop
      recorder.start(250);
      startTimeRef.current = Date.now();
      isRecordingRef.current = true;
      setState("recording");
      setDuration(0);

      // Duration timer
      timerRef.current = setInterval(() => {
        setDuration((prev) => prev + 1);
      }, 1000);

      // Audio analyser for waveform
      try {
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        if (AudioCtx) {
          const ctx = new AudioCtx();
          audioCtxRef.current = ctx;
          const analyser = ctx.createAnalyser();
          analyser.fftSize = 256;
          analyser.smoothingTimeConstant = 0.8;
          const source = ctx.createMediaStreamSource(stream);
          source.connect(analyser);
          setAnalyserNode(analyser);
        }
      } catch {
        // Analyser is optional — recording still works without it
      }

      return true;
    } catch (err: any) {
      console.error("Microphone access error:", err);

      let msg = "Mikrofonga ruxsat berilmadi.";
      if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
        if (inTelegram) {
          if (tgPlatform === "ios") {
            msg = "Telegram sozlamalarida mikrofon ruxsatini yoqing: iPhone Sozlamalar → Telegram → Mikrofon";
          } else if (tgPlatform === "android") {
            msg = "Telegram ilovasiga mikrofon ruxsatini bering: Sozlamalar → Ilovalar → Telegram → Ruxsatlar";
          } else {
            msg = "Telegram Desktop sozlamalarida mikrofon ruxsatini yoqing.";
          }
        }
      } else if (err.name === "NotFoundError") {
        msg = "Mikrofon topilmadi. Qurilmangizda mikrofon borligini tekshiring.";
      } else if (err.name === "NotReadableError") {
        msg = "Mikrofon boshqa ilova tomonidan band. Boshqa ilovalarni yoping.";
      }

      setError(msg);
      cleanup();
      setState("idle");
      return false;
    }
  }, [cleanup]);

  /* ── Stop → returns File ─────────────────────────────────────── */
  const stopRecording = useCallback((): Promise<File | null> => {
    return new Promise((resolve) => {
      if (!mediaRecorderRef.current || mediaRecorderRef.current.state === "inactive") {
        resolve(null);
        return;
      }

      // Enforce minimum duration
      const elapsed = Date.now() - startTimeRef.current;
      if (elapsed < MIN_DURATION_MS) {
        // Too short — cancel instead
        cleanup();
        setState("idle");
        setDuration(0);
        resolve(null);
        return;
      }

      setState("stopping");
      stopResolveRef.current = resolve;

      try {
        mediaRecorderRef.current.stop();
      } catch {
        // Already stopped
        resolve(null);
        stopResolveRef.current = null;
        cleanup();
        setState("idle");
        setDuration(0);
      }
    });
  }, [cleanup]);

  /* ── Cancel ──────────────────────────────────────────────────── */
  const cancelRecording = useCallback(() => {
    if (stopResolveRef.current) {
      stopResolveRef.current(null);
      stopResolveRef.current = null;
    }
    cleanup();
    setState("idle");
    setDuration(0);
  }, [cleanup]);

  return {
    state,
    duration,
    error,
    analyserNode,
    startRecording,
    stopRecording,
    cancelRecording,
  };
}
