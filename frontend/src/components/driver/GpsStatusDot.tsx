import React from "react";
import { useLocation } from "../../context/LocationContext";

export const GpsStatusDot: React.FC = () => {
  const { enabled, active } = useLocation();

  if (!enabled) return null;

  return (
    <span
      className="inline-flex items-center gap-2 rounded-full bg-emerald-500/10 border border-emerald-500/25 px-3 py-1.5"
      title={active ? "Jonli lokatsiya faol" : "Ulanmoqda…"}
    >
      <span className="relative flex h-3 w-3">
        {active && (
          <>
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
            <span className="absolute inline-flex h-full w-full animate-pulse rounded-full bg-emerald-300/40" />
          </>
        )}
        <span
          className={`relative inline-flex h-3 w-3 rounded-full shadow-[0_0_8px_rgba(52,211,153,0.8)] ${
            active ? "bg-emerald-400" : "bg-amber-400 animate-pulse"
          }`}
        />
      </span>
      <span className="text-[10px] font-bold text-emerald-300 uppercase tracking-widest">
        Live
      </span>
    </span>
  );
};
