import React, { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  MapPin,
  Flag,
  Route,
  Scale,
  Tag,
  Loader2,
  Check,
  Send,
  Navigation,
  Info
} from "lucide-react";
import L from "leaflet";

import {
  fetchOrder,
  acceptOrderDirectApi,
  createOrderOffer
} from "../../services/orderApi";
import { apiRequest } from "../../api";
import { useLocation } from "../../context/LocationContext";
import { useToast } from "../../components/ui/Toast";
import { Skeleton } from "../../components/ui/Skeleton";
import { OfferModal } from "../../components/driver/OfferModal";
import type { Order, OrderWaypoint } from "../../types/order";

interface RegionListItem {
  id: number;
  name_uz: string;
  centroid_lat?: number;
  centroid_lng?: number;
  bounds?: any;
}

interface DistrictListItem {
  id: number;
  region_id: number;
  name_uz: string;
  centroid_lat?: number;
  centroid_lng?: number;
  bounds?: any;
}

interface DistrictDetail extends DistrictListItem {
  geojson?: any;
}

interface RegionDetail extends RegionListItem {
  geojson?: any;
}

export const DriverOrderDetailPage: React.FC = () => {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { coords } = useLocation();

  const pk = Number(orderId);
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionBusy, setActionBusy] = useState<"accept" | "offer" | null>(null);
  const [showOfferModal, setShowOfferModal] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const mapLayersRef = useRef<L.Layer[]>([]);

  // Dynamically load Leaflet CSS
  useEffect(() => {
    const linkId = "leaflet-css-cdn";
    if (!document.getElementById(linkId)) {
      const link = document.createElement("link");
      link.id = linkId;
      link.rel = "stylesheet";
      link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
      document.head.appendChild(link);
    }
  }, []);

  // Fetch Order details
  const loadData = useCallback(async () => {
    if (!pk || Number.isNaN(pk)) {
      setErrorMsg("Noto'g'ri buyurtma ID");
      setLoading(false);
      return;
    }
    setLoading(true);
    setErrorMsg("");
    try {
      const data = await fetchOrder(pk);
      setOrder(data);
    } catch (ex: unknown) {
      const msg = ex instanceof Error ? ex.message : "Buyurtma yuklanmadi";
      setErrorMsg(msg);
      toast(msg, "error");
    } finally {
      setLoading(false);
    }
  }, [pk, toast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Geocode address based on DB regions & districts
  const geocodeWaypoint = async (
    wp: OrderWaypoint,
    regions: RegionListItem[]
  ): Promise<{ geojson?: any; lat?: number; lng?: number; bounds?: any; name?: string } | null> => {
    const addressLower = (wp.address || "").toLowerCase();
    let matchedRegion: RegionListItem | null = null;
    
    // 1. Find region match
    for (const reg of regions) {
      const regName = reg.name_uz.toLowerCase().replace(/['‘`’]/g, "");
      const normalizedAddress = addressLower.replace(/['‘`’]/g, "");
      if (
        normalizedAddress.includes(regName) ||
        normalizedAddress.includes(regName.replace(" viloyati", "").replace(" respublikasi", ""))
      ) {
        matchedRegion = reg;
        break;
      }
    }

    if (!matchedRegion) return null;

    // 2. Try to match district of this region
    try {
      const districts = await apiRequest<DistrictListItem[]>(
        `/geo/regions/${matchedRegion.id}/districts`
      );
      let matchedDistrict: DistrictListItem | null = null;
      for (const dist of districts) {
        const distName = dist.name_uz
          .toLowerCase()
          .replace(/['‘`’]/g, "")
          .replace(" tumani", "")
          .replace(" shahri", "");
        const normalizedAddress = addressLower.replace(/['‘`’]/g, "");
        if (normalizedAddress.includes(distName)) {
          matchedDistrict = dist;
          break;
        }
      }

      if (matchedDistrict) {
        const detail = await apiRequest<DistrictDetail>(
          `/geo/districts/${matchedDistrict.id}`
        );
        return {
          geojson: detail.geojson,
          lat: detail.centroid_lat,
          lng: detail.centroid_lng,
          bounds: detail.bounds,
          name: detail.name_uz
        };
      }
    } catch (err) {
      console.warn("Failed to fetch districts for geocoding:", err);
    }

    // Fallback to region
    try {
      const detail = await apiRequest<RegionDetail>(
        `/geo/regions/${matchedRegion.id}`
      );
      return {
        geojson: detail.geojson,
        lat: detail.centroid_lat,
        lng: detail.centroid_lng,
        bounds: detail.bounds,
        name: detail.name_uz
      };
    } catch (err) {
      console.warn("Failed to fetch region detail for geocoding:", err);
    }

    return null;
  };

  // Render Map markers, paths and polygons
  useEffect(() => {
    if (loading || !order || !mapContainerRef.current) return;

    // 1. Initialize Map if not present
    if (!mapRef.current) {
      mapRef.current = L.map(mapContainerRef.current, {
        zoomControl: true,
        scrollWheelZoom: true,
        crs: L.CRS.EPSG3395
      }).setView([41.2995, 69.2401], 8);

      L.tileLayer("https://core-renderer-tiles.maps.yandex.net/tiles?l=map&x={x}&y={y}&z={z}&scale=1&lang=uz_UZ", {
        attribution: "© Yandex.Maps"
      }).addTo(mapRef.current);
    }

    const map = mapRef.current;

    // Clear previous layers
    mapLayersRef.current.forEach((layer) => layer.remove());
    mapLayersRef.current = [];

    const drawMap = async () => {
      let regions: RegionListItem[] = [];
      try {
        regions = await apiRequest<RegionListItem[]>("/geo/regions");
      } catch (err) {
        console.warn("Could not fetch regions list:", err);
      }

      const activeLatLngs: L.LatLngExpression[] = [];
      const fitBoundsGroup: L.LatLngBounds = L.latLngBounds([]);

      // Custom marker icon creation helper
      const createCustomIcon = (type: string, seq: number) => {
        let color = "#10b981"; // pickup (green)
        if (type === "delivery") color = "#f43f5e"; // delivery (red)
        else if (type === "transit") color = "#8b5cf6"; // transit (purple)

        const svgHtml = `
          <div class="relative flex items-center justify-center">
            <span class="absolute inline-flex h-8 w-8 animate-ping rounded-full bg-white opacity-20"></span>
            <span class="relative flex h-8 w-8 items-center justify-center rounded-full border border-white/20 text-xs font-bold text-white shadow-lg" style="background-color: ${color}">
              ${seq}
            </span>
          </div>
        `;

        return L.divIcon({
          html: svgHtml,
          className: "custom-map-marker",
          iconSize: [32, 32],
          iconAnchor: [16, 16]
        });
      };

      const sortedWaypoints = [...(order.waypoints || [])].sort(
        (a, b) => a.sequence - b.sequence
      );

      for (let i = 0; i < sortedWaypoints.length; i++) {
        const wp = sortedWaypoints[i];
        const isPickup = wp.waypoint_type?.toLowerCase() === "pickup" || i === 0;
        const isDelivery =
          wp.waypoint_type?.toLowerCase() === "delivery" ||
          i === sortedWaypoints.length - 1;
        const wpType = isPickup ? "pickup" : isDelivery ? "delivery" : "transit";

        if (wp.latitude != null && wp.longitude != null) {
          const lat = Number(wp.latitude);
          const lng = Number(wp.longitude);
          const latlng: L.LatLngExpression = [lat, lng];

          activeLatLngs.push(latlng);
          fitBoundsGroup.extend(latlng);

          const marker = L.marker(latlng, {
            icon: createCustomIcon(wpType, i + 1)
          }).addTo(map);

          marker.bindPopup(`
            <div class="popup-info text-slate-950 font-sans p-1">
              <h5 class="font-bold text-xs uppercase text-slate-500">${i + 1}. ${wpType === "pickup" ? "Yuklash" : wpType === "delivery" ? "Yetkazish" : "Oraliq Nuqta"}</h5>
              <p class="font-semibold text-sm mt-0.5">${wp.address || "Manzilsiz"}</p>
              ${wp.note ? `<p class="text-xs text-slate-600 mt-1 italic">Qayd: ${wp.note}</p>` : ""}
            </div>
          `);

          mapLayersRef.current.push(marker);
        } else {
          // Address-based geocoding if coords are absent
          const geocoded = await geocodeWaypoint(wp, regions);
          if (geocoded) {
            const { geojson, lat, lng, name } = geocoded;

            if (geojson) {
              const geojsonLayer = L.geoJSON(geojson, {
                style: {
                  fillColor: wpType === "pickup" ? "#10b981" : wpType === "delivery" ? "#f43f5e" : "#8b5cf6",
                  fillOpacity: 0.25,
                  color: wpType === "pickup" ? "#10b981" : wpType === "delivery" ? "#f43f5e" : "#8b5cf6",
                  weight: 2,
                  dashArray: "4, 4"
                }
              }).addTo(map);

              geojsonLayer.bindPopup(`
                <div class="popup-info text-slate-950 font-sans p-1">
                  <h5 class="font-bold text-xs uppercase text-slate-500">${i + 1}. Hudud (${wpType === "pickup" ? "Yuklash" : wpType === "delivery" ? "Yetkazish" : "Oraliq"})</h5>
                  <p class="font-semibold text-sm mt-0.5">${name || wp.address}</p>
                </div>
              `);

              mapLayersRef.current.push(geojsonLayer);
            }

            if (lat != null && lng != null) {
              const latlng: L.LatLngExpression = [Number(lat), Number(lng)];
              activeLatLngs.push(latlng);
              fitBoundsGroup.extend(latlng);
            }
          }
        }
      }

      // Draw polyline connecting coordinates with arrows
      if (activeLatLngs.length >= 2) {
        const polyline = L.polyline(activeLatLngs, {
          color: "#06b6d4",
          weight: 4,
          opacity: 0.8,
          dashArray: "8, 8"
        }).addTo(map);

        mapLayersRef.current.push(polyline);

        // Add Direction chevron symbols at midpoints
        for (let idx = 0; idx < activeLatLngs.length - 1; idx++) {
          const p1 = map.latLngToContainerPoint(activeLatLngs[idx]);
          const p2 = map.latLngToContainerPoint(activeLatLngs[idx + 1]);

          // Midpoint logic
          const midX = (p1.x + p2.x) / 2;
          const midY = (p1.y + p2.y) / 2;
          const midLatLng = map.containerPointToLatLng([midX, midY]);

          const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x) * (180 / Math.PI);

          const arrowIcon = L.divIcon({
            html: `
              <div style="transform: rotate(${angle}deg); color: #06b6d4; font-size: 16px; font-weight: bold; text-shadow: 0 0 3px rgba(0,0,0,0.5);">
                ▶
              </div>
            `,
            className: "arrow-icon",
            iconSize: [20, 20],
            iconAnchor: [10, 10]
          });

          const arrowMarker = L.marker(midLatLng, { icon: arrowIcon }).addTo(map);
          mapLayersRef.current.push(arrowMarker);
        }
      }

      // Adjust map view
      if (coords?.latitude != null && coords?.longitude != null) {
        const myLatlng: L.LatLngExpression = [coords.latitude, coords.longitude];
        const myIcon = L.divIcon({
          html: `
            <div class="relative flex items-center justify-center">
              <span class="absolute inline-flex h-6 w-6 animate-ping rounded-full bg-cyan-400 opacity-75"></span>
              <span class="relative flex h-4 w-4 items-center justify-center rounded-full bg-cyan-500 border border-white shadow-lg"></span>
            </div>
          `,
          className: "my-location-marker",
          iconSize: [24, 24],
          iconAnchor: [12, 12]
        });
        const myMarker = L.marker(myLatlng, { icon: myIcon }).addTo(map);
        myMarker.bindPopup('<span class="text-xs font-semibold text-slate-900">Sizning joylashuvingiz</span>');
        mapLayersRef.current.push(myMarker);
        fitBoundsGroup.extend(myLatlng);
      }

      if (activeLatLngs.length > 0 || (coords?.latitude != null && coords?.longitude != null)) {
        map.fitBounds(fitBoundsGroup, {
          padding: [50, 50],
          maxZoom: 14
        });
      }
    };

    drawMap();
  }, [loading, order, coords]);

  // Clean map on unmount
  useEffect(() => {
    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  const handleLocateMe = () => {
    if (mapRef.current && coords?.latitude != null && coords?.longitude != null) {
      mapRef.current.flyTo([coords.latitude, coords.longitude], 15, { duration: 1 });
    }
  };

  // Accept directly handler
  const handleAcceptDirectly = async () => {
    if (!order) return;
    const confirm = window.confirm(
      `Siz ushbu buyurtmani ${Number(order.price).toLocaleString()} ${order.currency} narxi va ko'rsatilgan shartlari bilan qabul qilishga rozimisiz?`
    );
    if (!confirm) return;

    setActionBusy("accept");
    try {
      await acceptOrderDirectApi(order.id);
      toast("Buyurtma muvaffaqiyatli qabul qilindi!", "success");
      navigate("/driver/trips");
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Xatolik yuz berdi", "error");
    } finally {
      setActionBusy(null);
    }
  };

  const handleOfferClick = () => {
    setShowOfferModal(true);
  };

  const submitOffer = async (price: number, comment: string) => {
    if (!order) return;
    setActionBusy("offer");
    try {
      await createOrderOffer(order.id, {
        offered_price: price,
        currency: order.currency,
        comment: comment || "Qabul qilaman",
        driver_latitude: coords?.latitude ?? null,
        driver_longitude: coords?.longitude ?? null
      });
      toast("Sizning taklifingiz yuborildi", "success");
      setShowOfferModal(false);
      navigate("/driver/orders");
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Taklif yuborishda xatolik", "error");
    } finally {
      setActionBusy(null);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 px-4 py-5">
        <Skeleton className="h-10 w-1/3 rounded-xl" />
        <Skeleton className="h-64 w-full rounded-2xl" />
        <Skeleton className="h-40 w-full rounded-2xl" />
        <Skeleton className="h-24 w-full rounded-2xl" />
      </div>
    );
  }

  if (errorMsg || !order) {
    return (
      <div className="rounded-2xl border border-white/5 bg-slate-800/60 backdrop-blur-md p-6 shadow-lg text-center mx-4 mt-8">
        <p className="text-rose-400 text-sm font-medium">{errorMsg || "Buyurtma topilmadi"}</p>
        <button
          type="button"
          onClick={() => navigate("/driver/orders")}
          className="mt-4 rounded-xl bg-slate-700/50 px-4 py-2 text-sm font-semibold text-cyan-400 transition hover:bg-slate-600"
        >
          Yuklar ro'yxatiga qaytish
        </button>
      </div>
    );
  }

  const isPending = order.status?.toUpperCase() === "PENDING";
  const hasDriver = order.driver_id != null;
  const isAvailable = isPending && !hasDriver;

  return (
    <div className="space-y-4 pb-12">
      {/* HEADER SECTION */}
      <div className="min-w-0 px-1 pt-1">
        <h2 className="text-base font-bold text-white truncate">{order.cargo_name}</h2>
        <p className="text-xs text-slate-500">Buyurtma #{order.id}</p>
      </div>

      {/* MAP VIEWER CONTAINER */}
      <div className="relative rounded-2xl border border-white/5 bg-slate-800/60 overflow-hidden shadow-lg p-1.5 h-[300px]">
        <div ref={mapContainerRef} className="w-full h-full rounded-xl z-10"></div>
        {coords?.latitude != null && coords?.longitude != null && (
          <button
            type="button"
            onClick={handleLocateMe}
            className="absolute top-4 right-4 z-20 flex h-9 w-9 items-center justify-center rounded-xl bg-slate-950/85 backdrop-blur-md border border-white/10 text-cyan-400 hover:text-cyan-300 transition shadow-lg"
            title="Mening joylashuvim"
          >
            <Navigation size={18} />
          </button>
        )}
        <div className="absolute bottom-4 left-4 z-20 flex items-center gap-1.5 rounded-full bg-slate-950/85 backdrop-blur-md border border-white/10 px-3 py-1.5 text-[10px] text-slate-400">
          <Info size={12} className="text-cyan-400" />
          Marshrut nuqtalari tartib bilan bog'langan.
        </div>
      </div>

      {/* CARGO SPECS */}
      <section className="rounded-2xl border border-white/5 bg-slate-800/50 backdrop-blur-md p-5 shadow-lg space-y-4">
        <h3 className="text-sm font-bold text-slate-300">Buyurtma tafsilotlari</h3>
        
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center gap-2.5 bg-slate-900/40 rounded-xl p-3 border border-white/5">
            <Scale className="text-amber-400" size={18} />
            <div>
              <p className="text-[10px] text-slate-500 uppercase font-semibold">Yuk vazni</p>
              <p className="text-sm font-bold text-slate-200">{order.weight} Tonna</p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 bg-slate-900/40 rounded-xl p-3 border border-white/5">
            <Route className="text-cyan-400" size={18} />
            <div>
              <p className="text-[10px] text-slate-500 uppercase font-semibold">Masofa</p>
              <p className="text-sm font-bold text-slate-200">
                {order.total_distance_km ? `${order.total_distance_km} km` : "— km"}
              </p>
            </div>
          </div>

          <div className="col-span-2 flex items-center justify-between bg-slate-900/60 rounded-xl p-4 border border-white/10">
            <div className="flex items-center gap-2.5">
              <Tag className="text-emerald-400" size={18} />
              <div>
                <p className="text-[10px] text-slate-500 uppercase font-semibold">Taklif etilgan narx</p>
                <p className="text-lg font-bold text-white">
                  {Number(order.price).toLocaleString()} {order.currency}
                </p>
              </div>
            </div>
            <span className="rounded-lg bg-cyan-500/10 px-2.5 py-1 text-[10px] font-bold text-cyan-300 ring-1 ring-cyan-500/30 uppercase">
              {order.status}
            </span>
          </div>
        </div>
      </section>

      {/* WAYPOINTS ROUTE */}
      <section className="rounded-2xl border border-white/5 bg-slate-800/50 backdrop-blur-md p-5 shadow-lg">
        <h3 className="text-sm font-bold text-slate-300 mb-4">Marshrut nuqtalari</h3>
        
        <div className="space-y-0">
          {order.waypoints?.map((wp, index) => {
            const isFirst = index === 0;
            const isLast = index === (order.waypoints?.length ?? 1) - 1;
            const wpType = isFirst ? "pickup" : isLast ? "delivery" : "transit";
            const isLatLngPresent = wp.latitude != null && wp.longitude != null;

            return (
              <div key={wp.id} className="flex gap-3 relative">
                {!isLast && (
                  <span className="absolute left-[15px] top-8 bottom-0 w-0 border-l-2 border-dashed border-slate-700/80" />
                )}
                <span
                  className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ring-1 ${
                    wpType === "pickup"
                      ? "bg-emerald-500/20 text-emerald-300 ring-emerald-500/40"
                      : wpType === "delivery"
                      ? "bg-rose-500/20 text-rose-300 ring-rose-500/40"
                      : "bg-violet-500/20 text-violet-300 ring-violet-500/40"
                  }`}
                >
                  {wpType === "pickup" ? (
                    <MapPin size={16} />
                  ) : wpType === "delivery" ? (
                    <Flag size={16} />
                  ) : (
                    <Navigation size={16} />
                  )}
                </span>

                <div className={`flex-1 min-w-0 ${isLast ? "pb-0" : "pb-4"}`}>
                  <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                    {index + 1}. {wpType === "pickup" ? "Yuklash joyi" : wpType === "delivery" ? "Tushirish joyi" : "Oraliq nuqta"}
                  </p>
                  <p className="text-xs font-semibold text-slate-200 mt-0.5">{wp.address}</p>
                  {wp.note && <p className="text-xs text-slate-500 mt-1 pl-1 border-l border-white/5">{wp.note}</p>}
                  <p className="text-[10px] text-slate-600 mt-1 flex items-center gap-1.5">
                    <Navigation size={10} />
                    {isLatLngPresent ? `${wp.latitude}, ${wp.longitude}` : "Xaritada hudud belgilangan"}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* DRIVER ACTIONS */}
      {isAvailable && (
        <section className="px-1 pt-4 grid grid-cols-2 gap-3">
          <button
            type="button"
            disabled={actionBusy !== null}
            onClick={handleAcceptDirectly}
            className="w-full flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 py-3.5 text-xs font-bold text-white shadow-lg shadow-emerald-950/20 transition active:scale-[0.99] disabled:opacity-50"
          >
            {actionBusy === "accept" ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Check size={16} />
            )}
            Qabul qilish
          </button>

          <button
            type="button"
            disabled={actionBusy !== null}
            onClick={handleOfferClick}
            className="w-full flex items-center justify-center gap-2 rounded-2xl bg-slate-800/80 hover:bg-slate-700 border border-white/10 py-3.5 text-xs font-semibold text-slate-300 transition active:scale-[0.99] disabled:opacity-50"
          >
            {actionBusy === "offer" ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Send size={14} />
            )}
            Narx taklif qilish
          </button>
        </section>
      )}

      {/* MODALS */}
      <OfferModal
        isOpen={showOfferModal}
        onClose={() => setShowOfferModal(false)}
        onSubmit={submitOffer}
        orderPrice={order.price}
        orderCurrency={order.currency}
        busy={actionBusy === "offer"}
      />
    </div>
  );
};
