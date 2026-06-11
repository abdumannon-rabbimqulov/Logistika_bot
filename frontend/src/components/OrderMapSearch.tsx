import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  CircleMarker,
  GeoJSON,
  MapContainer,
  TileLayer,
  useMap,
  useMapEvents,
  Marker,
} from "react-leaflet";
import type { LatLngTuple, PathOptions } from "leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { CheckCircle2, MapPin, Navigation } from "lucide-react";
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

const normalizeGeoName = (name: string): string => {
  if (!name) return "";
  return name
    .toLowerCase()
    .replace(/['’‘ʻ`"]/g, "")
    .replace(/\b(viloyati|viloyat|shahar|shahri|tumani|tuman|respublikasi|respublika|province|region|district|city|state|area|county)\b/gi, "")
    .replace(/[^a-z0-9а-яёўқғҳ]/gi, "")
    .trim();
};

const isNameMatch = (dbName: string | null | undefined, inputName: string): boolean => {
  if (!dbName || !inputName) return false;
  const n1 = normalizeGeoName(dbName);
  const n2 = normalizeGeoName(inputName);
  return n1 === n2 || n1.includes(n2) || n2.includes(n1);
};

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
  onLocationPick,
  index,
}) => {
  const [step, setStep] = useState<MapSearchStep>(1);
  const [districts, setDistricts] = useState<District[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<RegionDetail | null>(null);
  const [selectedDistrict, setSelectedDistrict] = useState<DistrictDetail | null>(null);
  const [pickedLat, setPickedLat] = useState<number | null>(latitude);
  const [pickedLng, setPickedLng] = useState<number | null>(longitude);
  const [error, setError] = useState<string | null>(null);
  const [myLocation, setMyLocation] = useState<[number, number] | null>(null);
  const [manualFly, setManualFly] = useState<{ center: [number, number]; zoom: number } | null>(null);
  const [allRegions, setAllRegions] = useState<Region[]>([]);

  useEffect(() => {
    let active = true;
    fetchRegions()
      .then((data) => {
        if (active) setAllRegions(data);
      })
      .catch((err) => console.error("Viloyatlarni yuklashda xatolik:", err));
    return () => {
      active = false;
    };
  }, []);

  const handleLocateMe = () => {
    if (!navigator.geolocation) {
      alert("Geolokatsiya qurilmangiz tomonidan qo'llab-quvvatlanmaydi");
      return;
    }
    setError(null);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;
        setMyLocation([lat, lon]);
        setManualFly({ center: [lat, lon], zoom: POINT_ZOOM });
        setPickedLat(lat);
        setPickedLng(lon);

        try {
          const res = await fetch(
            `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lon}&format=json&accept-language=uz,ru,en`
          );
          if (!res.ok) throw new Error();
          const data = await res.json();
          const addr = data.address || {};

          const stateCandidate = addr.state || addr.region || addr.city || "";
          if (!stateCandidate) return;

          const matchedRegion = allRegions.find((r) => {
            return (
              isNameMatch(r.name_uz, stateCandidate) ||
              isNameMatch(r.name_ru, stateCandidate) ||
              isNameMatch(r.name_en, stateCandidate)
            );
          });

          if (!matchedRegion) return;

          const regionDetail = await fetchRegion(matchedRegion.id);
          setSelectedRegion(regionDetail);

          const districtsList = await fetchDistricts(matchedRegion.id);
          setDistricts(districtsList);

          const districtCandidate =
            addr.county ||
            addr.city_district ||
            addr.suburb ||
            addr.district ||
            addr.city ||
            addr.town ||
            addr.village ||
            addr.hamlet ||
            "";

          let matchedDistrict = districtsList.find((d) => {
            return (
              isNameMatch(d.name_uz, districtCandidate) ||
              isNameMatch(d.name_ru, districtCandidate) ||
              isNameMatch(d.name_en, districtCandidate)
            );
          });

          if (!matchedDistrict && districtCandidate) {
            matchedDistrict = districtsList.find((d) => {
              const normD = normalizeGeoName(d.name_uz);
              const normCand = normalizeGeoName(districtCandidate);
              return normD.includes(normCand) || normCand.includes(normD);
            });
          }

          if (matchedDistrict) {
            const districtDetail = await fetchDistrict(matchedDistrict.id);
            setSelectedDistrict(districtDetail);
            setStep(3);

            onLocationPick({
              regionId: matchedRegion.id,
              regionName: matchedRegion.name_uz,
              districtId: matchedDistrict.id,
              districtName: matchedDistrict.name_uz,
              latitude: lat,
              longitude: lon,
              address: `${matchedDistrict.name_uz}, ${matchedRegion.name_uz}`,
            });
          } else {
            setStep(2);
            setSelectedDistrict(null);

            onLocationPick({
              regionId: matchedRegion.id,
              regionName: matchedRegion.name_uz,
              districtId: 0,
              districtName: "",
              latitude: lat,
              longitude: lon,
              address: matchedRegion.name_uz,
            });
          }
        } catch (err) {
          console.error("Nominatim reverse geocoding failed:", err);
          setError("Joylashuv manzilini aniqlab bo'lmadi.");
        }
      },
      (err) => {
        console.error(err);
        alert("Joylashuvni aniqlashda xatolik yuz berdi");
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  useEffect(() => {
    if (!selectedRegion?.id) {
      setDistricts([]);
      return;
    }
    let cancelled = false;
    const loadDistricts = async () => {
      try {
        const data = await fetchDistricts(selectedRegion.id);
        if (!cancelled) setDistricts(data);
      } catch (ex: unknown) {
        if (!cancelled) setError(ex instanceof Error ? ex.message : "Tumanlar yuklanmadi");
      }
    };
    loadDistricts();
    return () => {
      cancelled = true;
    };
  }, [selectedRegion?.id]);

  const resetDistrict = useCallback(() => {
    setSelectedDistrict(null);
    setPickedLat(null);
    setPickedLng(null);
  }, []);



  const handleSelectRegion = useCallback(async (region: Region) => {
    setError(null);
    resetDistrict();
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
    try {
      const detail = await fetchDistrict(district.id);
      setSelectedDistrict(detail);
      setStep(3);

      onLocationPick({
        regionId: selectedRegion.id,
        regionName: selectedRegion.name_uz,
        districtId: detail.id,
        districtName: detail.name_uz,
        latitude: null,
        longitude: null,
        address: `${detail.name_uz}, ${selectedRegion.name_uz}`,
      });
    } catch (ex: unknown) {
      setError(ex instanceof Error ? ex.message : "Tuman yuklanmadi");
    }
  }, [selectedRegion, onLocationPick]);

  const handleMapPick = useCallback(
    (lat: number, lng: number) => {
      if (step !== 3 || !selectedRegion || !selectedDistrict) return;

      setPickedLat(lat);
      setPickedLng(lng);

      const builtAddress = `${selectedDistrict.name_uz}, ${selectedRegion.name_uz}`;

      onLocationPick({
        regionId: selectedRegion.id,
        regionName: selectedRegion.name_uz,
        districtId: selectedDistrict.id,
        districtName: selectedDistrict.name_uz,
        latitude: lat,
        longitude: lng,
        address: builtAddress,
      });
    },
    [step, selectedRegion, selectedDistrict, onLocationPick]
  );

  const flyCommand = useMemo((): MapFlyCommand => {
    if (manualFly) {
      return { mode: "flyPoint", center: manualFly.center, zoom: manualFly.zoom };
    }
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
  }, [step, selectedRegion, selectedDistrict, pickedLat, pickedLng, manualFly]);

  const regionGeo = toGeoJsonLayer(selectedRegion);
  const districtGeo = toGeoJsonLayer(selectedDistrict);
  const pointConfirmed = pickedLat != null && pickedLng != null;

  return (
    <div className="space-y-3">
      <div
        className={`rounded-xl px-3 py-2.5 text-sm font-medium ring-1 ${step === 3
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
            Viloyat
          </label>
          <select
            className="glass-input w-full"
            value={selectedRegion?.id || ""}
            onChange={(e) => {
              const rId = Number(e.target.value);
              const r = allRegions.find((reg) => reg.id === rId);
              if (r) {
                handleSelectRegion(r);
              } else {
                setSelectedRegion(null);
                setStep(1);
                resetDistrict();
              }
            }}
          >
            <option value="" style={{ backgroundColor: "#0f172a" }}>Viloyatni tanlang...</option>
            {allRegions.map((r) => (
              <option key={r.id} value={r.id} style={{ backgroundColor: "#0f172a" }}>
                {r.name_uz}
              </option>
            ))}
          </select>
        </div>

        {selectedRegion && (
          <div>
            <label className="block text-xs text-slate-500 mb-1 flex items-center gap-1">
              Tuman
            </label>
            <select
              className="glass-input w-full"
              value={selectedDistrict?.id || ""}
              onChange={(e) => {
                const dId = Number(e.target.value);
                const d = districts.find((dist) => dist.id === dId);
                if (d) {
                  handleSelectDistrict(d);
                } else {
                  setSelectedDistrict(null);
                  setStep(2);
                  setPickedLat(null);
                  setPickedLng(null);
                }
              }}
            >
              <option value="" style={{ backgroundColor: "#0f172a" }}>Tumanni tanlang...</option>
              {districts.map((d) => (
                <option key={d.id} value={d.id} style={{ backgroundColor: "#0f172a" }}>
                  {d.name_uz}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {error && (
        <p className="text-xs text-rose-400 bg-rose-500/10 rounded-lg px-3 py-2">{error}</p>
      )}

      <div className="relative rounded-xl overflow-hidden ring-1 ring-white/10">
        <div className="flex items-center gap-2 px-3 py-2 bg-slate-900/60 text-xs text-slate-400">
          <MapPin size={14} className="text-cyan-400" />
          {step < 3
            ? "Viloyat chegarasiga fitBounds · tuman tanlanganda flyTo"
            : `${pointLabel} nuqtasini xaritadan bosing`}
        </div>
        <button
          type="button"
          onClick={handleLocateMe}
          className="absolute top-10 right-4 z-20 flex h-9 w-9 items-center justify-center rounded-xl bg-slate-950/85 backdrop-blur-md border border-white/10 text-cyan-400 hover:text-cyan-300 transition shadow-lg"
          title="Mening joylashuvim"
        >
          <Navigation size={18} />
        </button>
        <MapContainer
          center={UZ_CENTER}
          zoom={DEFAULT_ZOOM}
          className="w-full z-0"
          style={{ height: 300 }}
          scrollWheelZoom
          crs={L.CRS.EPSG3395}
        >
          <TileLayer
            attribution="© Yandex.Maps"
            url="https://core-renderer-tiles.maps.yandex.net/tiles?l=map&x={x}&y={y}&z={z}&scale=1&lang=uz_UZ"
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
          {myLocation && (
            <CircleMarker
              center={myLocation}
              radius={7}
              pathOptions={{ color: "#06b6d4", weight: 2, fillColor: "#22d3ee", fillOpacity: 0.9 }}
            />
          )}
          {pickedLat != null && pickedLng != null && (
            <Marker
              position={[pickedLat, pickedLng]}
              icon={L.divIcon({
                html: `
                  <div class="relative flex items-center justify-center">
                    <span class="absolute inline-flex h-8 w-8 animate-ping rounded-full bg-white opacity-20"></span>
                    <span class="relative flex h-8 w-8 items-center justify-center rounded-full border border-white/20 text-xs font-bold text-white shadow-lg" style="background-color: ${index === 0 ? "#10b981" : "#f43f5e"
                  }">
                      ${index != null ? index + 1 : ""}
                    </span>
                  </div>
                `,
                className: "custom-map-marker",
                iconSize: [32, 32],
                iconAnchor: [16, 16]
              })}
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

      {selectedDistrict && selectedRegion && !pointConfirmed && (
        <div className="flex items-start gap-2 rounded-xl bg-violet-500/10 ring-1 ring-violet-500/25 px-3 py-2 text-xs text-violet-300">
          <CheckCircle2 size={16} className="shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Manzil tanlandi (xaritadan belgilash ixtiyoriy)</p>
            <p className="text-slate-400 mt-1">
              {selectedDistrict.name_uz}, {selectedRegion.name_uz}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
