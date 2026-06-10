import React from "react";
import { GripVertical, Trash2 } from "lucide-react";
import type { WaypointType } from "../types/order";
import type { MapSearchLocation } from "../types/geo";
import { OrderMapSearch } from "./OrderMapSearch";

export interface WaypointFormValues {
  localId: string;
  waypoint_type: WaypointType;
  address: string;
  note: string;
  latitude: number | null;
  longitude: number | null;
  region_id?: number | null;
  district_id?: number | null;
}

const TYPE_OPTIONS: { value: WaypointType; label: string }[] = [
  { value: "pickup", label: "Yuklash (Pickup)" },
  { value: "transit", label: "Oraliq (Transit)" },
  { value: "delivery", label: "Tushirish (Delivery)" },
];

export interface WaypointFormRowProps {
  index: number;
  value: WaypointFormValues;
  canRemove: boolean;
  onChange: (next: WaypointFormValues) => void;
  onRemove: () => void;
}

function pointLabel(type: WaypointType): string {
  if (type === "pickup") return "Yuklash";
  if (type === "delivery") return "Tushirish";
  return "Oraliq nuqta";
}

export const WaypointFormRow: React.FC<WaypointFormRowProps> = ({
  index,
  value,
  canRemove,
  onChange,
  onRemove,
}) => {
  const patch = (partial: Partial<WaypointFormValues>) => {
    onChange({ ...value, ...partial });
  };

  const handleLocationPick = (loc: MapSearchLocation) => {
    patch({
      latitude: loc.latitude,
      longitude: loc.longitude,
      address: loc.address || value.address,
      region_id: loc.regionId,
      district_id: loc.districtId,
    });
  };

  return (
    <div className="rounded-2xl bg-slate-900/50 ring-1 ring-white/10 p-3 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
          <GripVertical size={16} className="text-slate-600" />
          Nuqta #{index + 1}
        </div>
        {canRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="p-1.5 rounded-lg text-rose-400 hover:bg-rose-500/10"
            aria-label="Nuqtani o'chirish"
          >
            <Trash2 size={16} />
          </button>
        )}
      </div>

      <div>
        <label className="block text-xs text-slate-500 mb-1">Nuqta turi</label>
        <select
          className="glass-input w-full"
          value={value.waypoint_type}
          onChange={(e) => patch({ waypoint_type: e.target.value as WaypointType })}
        >
          {TYPE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <OrderMapSearch
        pointLabel={pointLabel(value.waypoint_type)}
        latitude={value.latitude}
        longitude={value.longitude}
        onLocationPick={handleLocationPick}
        index={index}
      />

      <div>
        <label className="block text-xs text-slate-500 mb-1">Izoh</label>
        <textarea
          className="glass-input w-full min-h-[64px] resize-y"
          placeholder="Qo'shimcha ma'lumot..."
          value={value.note}
          onChange={(e) => patch({ note: e.target.value })}
          rows={2}
        />
      </div>
    </div>
  );
};

export function createWaypoint(
  type: WaypointType = "pickup",
  partial?: Partial<WaypointFormValues>
): WaypointFormValues {
  return {
    localId: crypto.randomUUID(),
    waypoint_type: type,
    address: "",
    note: "",
    latitude: null,
    longitude: null,
    region_id: null,
    district_id: null,
    ...partial,
  };
}
