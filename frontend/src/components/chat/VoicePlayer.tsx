import React, { useState, useRef, useEffect } from "react";
import { Play, Pause } from "lucide-react";

interface VoicePlayerProps {
  src: string;
  onFinishedListening?: () => void;
}

export const VoicePlayer: React.FC<VoicePlayerProps> = ({ src, onFinishedListening }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [playbackRate, setPlaybackRate] = useState<1 | 1.5 | 2>(1);
  const [hasFinished, setHasFinished] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    const audio = new Audio(src);
    audioRef.current = audio;

    const setAudioData = () => {
      setDuration(audio.duration);
    };

    const setAudioTime = () => {
      setCurrentTime(audio.currentTime);
      setProgress((audio.currentTime / audio.duration) * 100);
    };

    const onAudioEnd = () => {
      setIsPlaying(false);
      setProgress(0);
      setCurrentTime(0);
      if (!hasFinished) {
        setHasFinished(true);
        onFinishedListening?.();
      }
    };

    audio.addEventListener("loadedmetadata", setAudioData);
    audio.addEventListener("timeupdate", setAudioTime);
    audio.addEventListener("ended", onAudioEnd);

    return () => {
      audio.removeEventListener("loadedmetadata", setAudioData);
      audio.removeEventListener("timeupdate", setAudioTime);
      audio.removeEventListener("ended", onAudioEnd);
      audio.pause();
    };
  }, [src, onFinishedListening, hasFinished]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.playbackRate = playbackRate;
    }
  }, [playbackRate]);

  const togglePlayPause = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!audioRef.current) return;
    const newTime = (Number(e.target.value) / 100) * duration;
    audioRef.current.currentTime = newTime;
    setProgress(Number(e.target.value));
  };

  const toggleSpeed = () => {
    setPlaybackRate(prev => {
      if (prev === 1) return 1.5;
      if (prev === 1.5) return 2;
      return 1;
    });
  };

  const formatTime = (secs: number) => {
    if (!secs || isNaN(secs)) return "00:00";
    const m = Math.floor(secs / 60).toString().padStart(2, "0");
    const s = Math.floor(secs % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  return (
    <div className="tg-voice-player">
      <button className="tg-vp-play-btn" onClick={togglePlayPause}>
        {isPlaying ? <Pause size={18} /> : <Play size={18} style={{ marginLeft: 2 }} />}
      </button>
      
      <div className="tg-vp-timeline-wrap">
        {/* We use a simple range input for waveform approximation for now */}
        <input 
          type="range" 
          min="0" 
          max="100" 
          value={isNaN(progress) ? 0 : progress} 
          onChange={handleSeek} 
          className="tg-vp-slider" 
        />
        <div className="tg-vp-time">
          <span>{formatTime(currentTime)}</span>
          {/*<span>{formatTime(duration)}</span>*/}
        </div>
      </div>
      
      <button className="tg-vp-speed-btn" onClick={toggleSpeed}>
        {playbackRate}x
      </button>
    </div>
  );
};
