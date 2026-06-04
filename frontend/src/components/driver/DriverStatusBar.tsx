import React, { useEffect, useState } from "react";
import { fetchDriverMe } from "../../services/driverApi";
import { useLocation } from "../../context/LocationContext";
import type { DriverProfile } from "../../types/driver";

export const DriverStatusBar: React.FC = () => {
  const { enabled, active, toggle, error } = useLocation();
  const [profile, setProfile] = useState<DriverProfile | null>(null);

  useEffect(() => {
    fetchDriverMe()
      .then(setProfile)
      .catch(() => setProfile(null));
  }, [enabled, active]);

  const isLive =
    profile?.user_status === "LIVE" || (enabled && active);

  return (
    <div className="flex items-center justify-between gap-3 py-1">
      <div
        className={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-bold tracking-wide ${
          isLive
            ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
            : "bg-slate-800/80 text-slate-400 border border-white/10"
        }`}
      >
        <span className="relative flex h-2 w-2">
          {isLive && (
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-70" />
          )}
          <span
            className={`relative h-2 w-2 rounded-full ${
              isLive ? "bg-emerald-400" : "bg-slate-500"
            }`}
          />
        </span>
        {isLive ? "LIVE" : "OFFLINE"}
      </div>

      <div className="flex flex-col items-end gap-0.5">
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          aria-label="GPS"
          onClick={toggle}
          className={`relative h-7 w-12 rounded-full transition-colors duration-200 shrink-0 ${
            enabled ? "bg-emerald-500" : "bg-slate-600"
          }`}
        >
          <span
            className={`absolute top-0.5 h-6 w-6 rounded-full bg-white shadow-md transition-all duration-200 ${
              enabled ? "left-[22px]" : "left-0.5"
            }`}
          />
        </button>
        <span className="text-[9px] font-semibold uppercase tracking-wider text-slate-500">
          GPS {enabled ? "on" : "off"}
        </span>
      </div>
      {error && (
        <p className="absolute left-4 right-4 top-full mt-1 text-[10px] text-rose-400 truncate">
          {error}
        </p>
      )}
    </div>
  );
};
