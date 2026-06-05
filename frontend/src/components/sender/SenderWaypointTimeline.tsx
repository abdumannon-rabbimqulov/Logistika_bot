import React from "react";
import { MapPin, Navigation } from "lucide-react";
import type { OrderWaypoint } from "../../types/order";

const TYPE_LABEL: Record<string, string> = {
  pickup: "Yuklash",
  delivery: "Tushirish",
  transit: "Oraliq",
};

function typeLabel(type: string): string {
  return TYPE_LABEL[type.toLowerCase()] ?? type;
}

function typeColor(type: string): string {
  if (type === "pickup") return "bg-emerald-500/20 text-emerald-300 ring-emerald-500/40";
  if (type === "delivery") return "bg-violet-500/20 text-violet-300 ring-violet-500/40";
  return "bg-slate-700/80 text-slate-300 ring-white/10";
}

export const SenderWaypointTimeline: React.FC<{ waypoints: OrderWaypoint[] }> = ({ waypoints }) => {
  const sorted = [...waypoints].sort((a, b) => a.sequence - b.sequence);
  if (sorted.length === 0) return null;

  return (
    <ol className="space-y-0">
      {sorted.map((wp, index) => (
        <li key={wp.id} className="flex gap-3">
          <div className="flex flex-col items-center">
            <span
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ring-1 ${typeColor(
                wp.waypoint_type
              )}`}
            >
              {index + 1}
            </span>
            {index < sorted.length - 1 && (
              <span className="my-1 w-px flex-1 min-h-[12px] bg-gradient-to-b from-cyan-500/50 to-violet-500/30" />
            )}
          </div>
          <div className={`pb-3 min-w-0 flex-1 ${index === sorted.length - 1 ? "pb-0" : ""}`}>
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              {typeLabel(wp.waypoint_type)}
            </p>
            <p className="text-sm text-slate-200 flex items-start gap-1.5 mt-0.5">
              <MapPin size={14} className="text-cyan-400 shrink-0 mt-0.5" />
              <span className="break-words">{wp.address}</span>
            </p>
            {wp.note && (
              <p className="text-xs text-slate-500 mt-0.5 pl-5">{wp.note}</p>
            )}
            {wp.latitude != null && wp.longitude != null && (
              <p className="text-[10px] text-slate-600 mt-1 pl-5 flex items-center gap-1">
                <Navigation size={10} />
                {wp.latitude.toFixed(5)}, {wp.longitude.toFixed(5)}
              </p>
            )}
          </div>
        </li>
      ))}
    </ol>
  );
};
