import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  CircleMarker,
  GeoJSON,
  MapContainer,
  TileLayer,
  useMap,
  useMapEvents,
} from "react-leaflet";
import type { LatLngTuple, PathOptions } from "leaflet";
import "leaflet/dist/leaflet.css";
import { CheckCircle2, MapPin, Search } from "lucide-react";
import { fetchDistrict, fetchDistricts, fetchRegion, fetchRegions } from "../services/geoApi";
import type {
  District,
  DistrictDetail,
  MapFlyCommand,
  MapSearchStep,
  OrderMapSearchProps,
  Region,
  RegionDetail,
} from "../types/geo";
import { boundsToLeaflet } from "../types/geo";

const UZ_CENTER: LatLngTuple = [41.311081, 69.279737];
const DEFAULT_ZOOM = 6;
const DISTRICT_ZOOM = 12;
const POINT_ZOOM = 16;

const REGION_STYLE: PathOptions = {
  color: "#22d3ee",
  weight: 3,
  fillColor: "#06b6d4",
  fillOpacity: 0.2,
};

const DISTRICT_STYLE: PathOptions = {
  color: "#a78bfa",
  weight: 3,
  fillColor: "#8b5cf6",
  fillOpacity: 0.32,
};

const STEP_HINTS: Record<MapSearchStep, string> = {
  1: "Viloyatni tanlang yoki yozing.",
  2: "Iltimos, tumanni tanlang yoki yozing.",
  3: "Iltimos, yuk ortish/tushirishning aniq nuqtasini xaritadan bosing.",
};

interface MapFlyControllerProps {
  command: MapFlyCommand;
}

/** react-leaflet useMap — dinamik fitBounds / flyTo (asinxron xatosiz) */
const MapFlyController: React.FC<MapFlyControllerProps> = ({ command }) => {
  const map = useMap();

  useEffect(() => {
    if (command.mode === "idle") return;

    const run = () => {
      if (command.mode === "fitRegion" && command.bounds) {
        map.fitBounds(command.bounds, { padding: [32, 32], maxZoom: 10, animate: true });
        return;
      }
      if (
        (command.mode === "flyDistrict" || command.mode === "flyPoint") &&
        command.center
      ) {
        map.flyTo(command.center, command.zoom ?? DISTRICT_ZOOM, { duration: 0.9 });
      }
    };

    // Xarita DOM ga to'liq mount bo'lgach ishga tushirish
    const timer = window.setTimeout(run, 50);
    return () => window.clearTimeout(timer);
  }, [command, map]);

  return null;
};

interface MapClickHandlerProps {
  enabled: boolean;
  onPick: (lat: number, lng: number) => void;
}

const MapClickHandler: React.FC<MapClickHandlerProps> = ({ enabled, onPick }) => {
  useMapEvents({
    click(e) {
      if (!enabled) return;
      onPick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
};

function toGeoJsonLayer(
  payload: RegionDetail | DistrictDetail | null
): GeoJSON.Feature | GeoJSON.FeatureCollection | null {
  if (!payload?.geojson) return null;
  const g = payload.geojson;
  if (g.type === "Feature" || g.type === "FeatureCollection") {
    return g as GeoJSON.Feature | GeoJSON.FeatureCollection;
  }
  return {
    type: "Feature",
    properties: {},
    geometry: g as GeoJSON.Geometry,
  } as GeoJSON.Feature;
}

export type { OrderMapSearchProps };

export const OrderMapSearch: React.FC<OrderMapSearchProps> = ({
  pointLabel = "nuqta",
  latitude = null,
  longitude = null,
  address = "",
  onLocationPick,
}) => {
  const [step, setStep] = useState<MapSearchStep>(1);
  const [regionQuery, setRegionQuery] = useState("");
  const [districtQuery, setDistrictQuery] = useState("");
  const [regions, setRegions] = useState<Region[]>([]);
  const [districts, setDistricts] = useState<District[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<RegionDetail | null>(null);
  const [selectedDistrict, setSelectedDistrict] = useState<DistrictDetail | null>(null);
  const [pickedLat, setPickedLat] = useState<number | null>(latitude);
  const [pickedLng, setPickedLng] = useState<number | null>(longitude);
  const [loadingRegions, setLoadingRegions] = useState(false);
  const [loadingDistricts, setLoadingDistricts] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setLoadingRegions(true);
      try {
        const data = await fetchRegions(regionQuery || undefined);
        if (!cancelled) setRegions(data);
      } catch (ex: unknown) {
        if (!cancelled) setError(ex instanceof Error ? ex.message : "Viloyatlar yuklanmadi");
      } finally {
        if (!cancelled) setLoadingRegions(false);
      }
    }, 280);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [regionQuery]);

  useEffect(() => {
    if (!selectedRegion?.id) {
      setDistricts([]);
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setLoadingDistricts(true);
      try {
        const data = await fetchDistricts(selectedRegion.id, districtQuery || undefined);
        if (!cancelled) setDistricts(data);
      } catch (ex: unknown) {
        if (!cancelled) setError(ex instanceof Error ? ex.message : "Tumanlar yuklanmadi");
      } finally {
        if (!cancelled) setLoadingDistricts(false);
      }
    }, 280);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [selectedRegion?.id, districtQuery]);

  const resetDistrict = useCallback(() => {
    setSelectedDistrict(null);
    setPickedLat(null);
    setPickedLng(null);
  }, []);

  const handleSelectRegion = useCallback(async (region: Region) => {
    setError(null);
    resetDistrict();
    setDistrictQuery("");
    setRegionQuery(region.name_uz);
    try {
      const detail = await fetchRegion(region.id);
      setSelectedRegion(detail);
      setStep(2);
    } catch (ex: unknown) {
      setError(ex instanceof Error ? ex.message : "Viloyat yuklanmadi");
    }
  }, [resetDistrict]);

  const handleSelectDistrict = useCallback(async (district: District) => {
    if (!selectedRegion) return;
    setError(null);
    setPickedLat(null);
    setPickedLng(null);
    setDistrictQuery(district.name_uz);
    try {
      const detail = await fetchDistrict(district.id);
      setSelectedDistrict(detail);
      setStep(3);
    } catch (ex: unknown) {
      setError(ex instanceof Error ? ex.message : "Tuman yuklanmadi");
    }
  }, [selectedRegion]);

  const handleMapPick = useCallback(
    (lat: number, lng: number) => {
      if (step !== 3 || !selectedRegion || !selectedDistrict) return;

      setPickedLat(lat);
      setPickedLng(lng);

      const builtAddress = [
        selectedDistrict.name_uz,
        selectedRegion.name_uz,
        `${lat.toFixed(5)}, ${lng.toFixed(5)}`,
      ].join(", ");

      onLocationPick({
        regionId: selectedRegion.id,
        regionName: selectedRegion.name_uz,
        districtId: selectedDistrict.id,
        districtName: selectedDistrict.name_uz,
        latitude: lat,
        longitude: lng,
        address: address.trim() || builtAddress,
      });
    },
    [step, selectedRegion, selectedDistrict, onLocationPick, address]
  );

  const flyCommand = useMemo((): MapFlyCommand => {
    if (pickedLat != null && pickedLng != null) {
      return { mode: "flyPoint", center: [pickedLat, pickedLng], zoom: POINT_ZOOM };
    }
    if (step === 3 && selectedDistrict) {
      const center: [number, number] | null =
        selectedDistrict.centroid_lat != null && selectedDistrict.centroid_lng != null
          ? [selectedDistrict.centroid_lat, selectedDistrict.centroid_lng]
          : null;
      if (center) {
        return { mode: "flyDistrict", center, zoom: DISTRICT_ZOOM };
      }
      const dbounds = boundsToLeaflet(selectedDistrict.bounds);
      if (dbounds) {
        return { mode: "fitRegion", bounds: dbounds };
      }
    }
    if (step >= 2 && selectedRegion) {
      const rbounds = boundsToLeaflet(selectedRegion.bounds);
      if (rbounds) {
        return { mode: "fitRegion", bounds: rbounds };
      }
      if (selectedRegion.centroid_lat != null && selectedRegion.centroid_lng != null) {
        return {
          mode: "flyDistrict",
          center: [selectedRegion.centroid_lat, selectedRegion.centroid_lng],
          zoom: 8,
        };
      }
    }
    return { mode: "idle" };
  }, [step, selectedRegion, selectedDistrict, pickedLat, pickedLng]);

  const regionGeo = toGeoJsonLayer(selectedRegion);
  const districtGeo = toGeoJsonLayer(selectedDistrict);
  const pointConfirmed = pickedLat != null && pickedLng != null;

  return (
    <div className="space-y-3">
      <div
        className={`rounded-xl px-3 py-2.5 text-sm font-medium ring-1 ${
          step === 3
            ? "bg-violet-500/15 text-violet-200 ring-violet-500/30"
            : step === 2
              ? "bg-cyan-500/15 text-cyan-200 ring-cyan-500/30"
              : "bg-slate-800/80 text-slate-400 ring-white/10"
        }`}
      >
        <span className="text-xs opacity-60 block mb-0.5">Bosqich {step}/3</span>
        {STEP_HINTS[step]}
      </div>

      <div className="grid grid-cols-1 gap-3">
        <div>
          <label className="block text-xs text-slate-500 mb-1 flex items-center gap-1">
            <Search size={12} />
            Viloyat
          </label>
          <input
            type="text"
            className="glass-input w-full"
            placeholder="Masalan: Toshkent, Samarqand..."
            value={regionQuery}
            onChange={(e) => {
              setRegionQuery(e.target.value);
              if (step > 1) {
                setStep(1);
                setSelectedRegion(null);
                resetDistrict();
              }
            }}
            list="region-suggestions"
          />
          <datalist id="region-suggestions">
            {regions.map((r) => (
              <option key={r.id} value={r.name_uz} />
            ))}
          </datalist>
          {regionQuery && !loadingRegions && regions.length > 0 && step === 1 && (
            <ul className="mt-1 max-h-36 overflow-y-auto rounded-xl bg-slate-900 ring-1 ring-white/10">
              {regions.slice(0, 8).map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    className="w-full text-left px-3 py-2 text-sm hover:bg-cyan-500/10 text-slate-200"
                    onClick={() => handleSelectRegion(r)}
                  >
                    {r.name_uz}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {selectedRegion && (
          <div>
            <label className="block text-xs text-slate-500 mb-1 flex items-center gap-1">
              <Search size={12} />
              Tuman
            </label>
            <input
              type="text"
              className="glass-input w-full"
              placeholder="Tumanni tanlang yoki yozing..."
              value={districtQuery}
              onChange={(e) => {
                setDistrictQuery(e.target.value);
                if (step > 2) {
                  setStep(2);
                  resetDistrict();
                }
              }}
              list="district-suggestions"
            />
            <datalist id="district-suggestions">
              {districts.map((d) => (
                <option key={d.id} value={d.name_uz} />
              ))}
            </datalist>
            {districtQuery && !loadingDistricts && districts.length > 0 && step === 2 && (
              <ul className="mt-1 max-h-36 overflow-y-auto rounded-xl bg-slate-900 ring-1 ring-white/10">
                {districts.slice(0, 10).map((d) => (
                  <li key={d.id}>
                    <button
                      type="button"
                      className="w-full text-left px-3 py-2 text-sm hover:bg-violet-500/10 text-slate-200"
                      onClick={() => handleSelectDistrict(d)}
                    >
                      {d.name_uz}
                      {!d.has_geometry && (
                        <span className="ml-2 text-[10px] text-slate-500">(faqat nom)</span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {error && (
        <p className="text-xs text-rose-400 bg-rose-500/10 rounded-lg px-3 py-2">{error}</p>
      )}

      <div className="rounded-xl overflow-hidden ring-1 ring-white/10">
        <div className="flex items-center gap-2 px-3 py-2 bg-slate-900/60 text-xs text-slate-400">
          <MapPin size={14} className="text-cyan-400" />
          {step < 3
            ? "Viloyat chegarasiga fitBounds · tuman tanlanganda flyTo"
            : `${pointLabel} nuqtasini xaritadan bosing`}
        </div>
        <MapContainer
          center={UZ_CENTER}
          zoom={DEFAULT_ZOOM}
          className="w-full z-0"
          style={{ height: 300 }}
          scrollWheelZoom
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapFlyController command={flyCommand} />
          <MapClickHandler enabled={step === 3} onPick={handleMapPick} />

          {regionGeo && step >= 2 && (
            <GeoJSON
              key={`region-${selectedRegion?.id}`}
              data={regionGeo}
              style={() => REGION_STYLE}
            />
          )}
          {districtGeo && step >= 3 && (
            <GeoJSON
              key={`district-${selectedDistrict?.id}`}
              data={districtGeo}
              style={() => DISTRICT_STYLE}
            />
          )}
          {pickedLat != null && pickedLng != null && (
            <CircleMarker
              center={[pickedLat, pickedLng]}
              radius={9}
              pathOptions={{ color: "#22d3ee", weight: 2, fillColor: "#06b6d4", fillOpacity: 0.9 }}
            />
          )}
        </MapContainer>
      </div>

      {pointConfirmed && (
        <div className="flex items-start gap-2 rounded-xl bg-emerald-500/10 ring-1 ring-emerald-500/25 px-3 py-2 text-xs text-emerald-300">
          <CheckCircle2 size={16} className="shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Koordinata saqlandi</p>
            <p className="text-emerald-400/80 mt-0.5">
              {pickedLat!.toFixed(6)}, {pickedLng!.toFixed(6)}
            </p>
            {selectedDistrict && selectedRegion && (
              <p className="text-slate-400 mt-1">
                {selectedDistrict.name_uz}, {selectedRegion.name_uz}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
