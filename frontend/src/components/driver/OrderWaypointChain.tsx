import React from "react";
import { MapPin } from "lucide-react";
import type { OrderWaypoint } from "../../types/order";

const TYPE_LABEL: Record<string, string> = {
  origin: "Jo'nash",
  destination: "Manzil",
  transit: "Oraliq",
};

function typeLabel(type: string): string {
  return TYPE_LABEL[type.toLowerCase()] ?? type;
}

export const OrderWaypointChain: React.FC<{ waypoints: OrderWaypoint[] }> = ({ waypoints }) => {
  const sorted = [...waypoints].sort((a, b) => a.sequence - b.sequence);
  if (sorted.length === 0) return null;

  return (
    <ol className="space-y-0">
      {sorted.map((wp, index) => (
        <li key={wp.id} className="flex gap-3">
          <div className="flex flex-col items-center">
            <span
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                wp.waypoint_type === "origin"
                  ? "bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/40"
                  : wp.waypoint_type === "destination"
                    ? "bg-violet-500/20 text-violet-300 ring-1 ring-violet-500/40"
                    : "bg-slate-700/80 text-slate-300 ring-1 ring-white/10"
              }`}
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
            {wp.landmark && (
              <p className="text-xs text-slate-500 mt-0.5 pl-5">{wp.landmark}</p>
            )}
          </div>
          {index < sorted.length - 1 && (
            <span className="sr-only">→</span>
          )}
        </li>
      ))}
    </ol>
  );
};
