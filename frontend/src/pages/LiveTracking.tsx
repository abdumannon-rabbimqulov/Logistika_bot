import React, { useEffect, useRef, useState } from "react";
import { getWebSocketUrl } from "../api";
import type { DriverLocation } from "../types";
import { Users, Radio, Navigation, Info, Clock } from "lucide-react";
import L from "leaflet";

export const LiveTracking: React.FC = () => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersRef = useRef<Record<number, L.Marker>>({});

  const [drivers, setDrivers] = useState<DriverLocation[]>([]);
  const [selectedDriverId, setSelectedDriverId] = useState<number | null>(null);
  const [wsStatus, setWsStatus] = useState<"connecting" | "online" | "offline">("connecting");
  const [errorMsg, setErrorMsg] = useState("");

  // Dynamically load Leaflet CSS on mount
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

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    // Tashkent coordinates default
    const map = L.map(mapContainerRef.current, {
      crs: L.CRS.EPSG3395
    }).setView([41.2995, 69.2401], 12);

    L.tileLayer("https://core-renderer-tiles.maps.yandex.net/tiles?l=map&x={x}&y={y}&z={z}&scale=1&lang=uz_UZ", {
      attribution: "© Yandex.Maps",
    }).addTo(map);

    mapRef.current = map;

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // Fetch initial drivers & Connect WebSocket
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    const connectWebSocket = () => {
      if (cancelled) return;
      setWsStatus("connecting");
      const token = localStorage.getItem("logistika_access_token") || "";
      const wsUrl = getWebSocketUrl(`/system/drivers/locations/stream?token=${token}`);

      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsStatus("online");
        setErrorMsg("");
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === "snapshot") {
            const snapshot = data.items as DriverLocation[];
            setDrivers(snapshot);
            updateMapMarkers(snapshot);
          } else if (data.event === "update") {
            const updatedDriver = data.item as DriverLocation;
            setDrivers((prev) => {
              const exists = prev.some((d) => d.driver_id === updatedDriver.driver_id);
              if (exists) {
                return prev.map((d) => (d.driver_id === updatedDriver.driver_id ? updatedDriver : d));
              } else {
                return [...prev, updatedDriver];
              }
            });
            updateSingleMarker(updatedDriver);
          }
        } catch (err) {
          console.error("WS message parse failed:", err);
        }
      };

      ws.onclose = () => {
        setWsStatus("offline");
        if (!cancelled) {
          reconnectTimeout = setTimeout(connectWebSocket, 5000);
        }
      };

      ws.onerror = (err) => {
        console.error("WS Connection error:", err);
        setWsStatus("offline");
      };
    };

    connectWebSocket();

    return () => {
      cancelled = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, []);

  // Helper to construct SVG Marker Icon
  const createMarkerIcon = (isActive: boolean) => {
    const color = isActive ? "#00e676" : "#ff1744"; // green vs red
    const svgHtml = `
      <svg width="32" height="32" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg">
        <circle cx="16" cy="16" r="10" fill="${color}" fill-opacity="0.2" stroke="${color}" stroke-width="2"/>
        <circle cx="16" cy="16" r="6" fill="${color}"/>
        <path d="M16 2 L22 14 L16 10 L10 14 Z" fill="${color}" transform="rotate(45 16 16)"/>
      </svg>
    `;
    return L.divIcon({
      html: svgHtml,
      className: "custom-driver-icon",
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    });
  };

  // Update single driver marker position on map
  const updateSingleMarker = (driver: DriverLocation) => {
    const map = mapRef.current;
    if (!map) return;

    const { driver_id, lat, lon, full_name, truck_number } = driver;
    const isOnline = true; // live updates mean they are active

    if (markersRef.current[driver_id]) {
      // Move existing marker
      markersRef.current[driver_id].setLatLng([lat, lon]);
    } else {
      // Create new marker
      const marker = L.marker([lat, lon], {
        icon: createMarkerIcon(isOnline),
      }).addTo(map);

      marker.bindPopup(`
        <div class="popup-info">
          <h4>${full_name || `Haydovchi ID: ${driver_id}`}</h4>
          <p><b>Raqami:</b> ${truck_number || "Yo'q"}</p>
          <p><b>Lat:</b> ${lat.toFixed(5)}, <b>Lon:</b> ${lon.toFixed(5)}</p>
        </div>
      `);

      markersRef.current[driver_id] = marker;
    }
  };

  // Update all map markers
  const updateMapMarkers = (locationItems: DriverLocation[]) => {
    const map = mapRef.current;
    if (!map) return;

    // Clear old markers not in snapshot
    const itemIds = locationItems.map((d) => d.driver_id);
    Object.keys(markersRef.current).forEach((key) => {
      const id = Number(key);
      if (!itemIds.includes(id)) {
        markersRef.current[id].remove();
        delete markersRef.current[id];
      }
    });

    // Add or update markers
    locationItems.forEach((d) => {
      updateSingleMarker(d);
    });

    // Fit map bounds to show all markers if any exist
    if (locationItems.length > 0) {
      const bounds = L.latLngBounds(locationItems.map((d) => [d.lat, d.lon]));
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
    }
  };

  // Focus Map on clicked driver
  const handleDriverClick = (driver: DriverLocation) => {
    setSelectedDriverId(driver.driver_id);
    const map = mapRef.current;
    if (map) {
      map.setView([driver.lat, driver.lon], 15);
      if (markersRef.current[driver.driver_id]) {
        markersRef.current[driver.driver_id].openPopup();
      }
    }
  };

  return (
    <div className="live-tracking-page">
      <div className="tracking-layout">
        {/* SIDEBAR: ACTIVE DRIVERS LIST */}
        <div className="drivers-sidebar glass-card">
          <div className="sidebar-header-row">
            <h4><Users size={16} /> Online Haydovchilar</h4>
            <div className={`status-pill ws-status ${wsStatus}`}>
              <Radio size={12} className={wsStatus === "online" ? "pulsing-icon" : ""} />
              {wsStatus === "online" ? "Jonli" : wsStatus === "connecting" ? "Ulanmoqda" : "Oflayn"}
            </div>
          </div>

          <div className="drivers-list">
            {drivers.length > 0 ? (
              drivers.map((d) => (
                <div
                  key={d.driver_id}
                  className={`driver-item ${selectedDriverId === d.driver_id ? "selected" : ""}`}
                  onClick={() => handleDriverClick(d)}
                >
                  <div className="driver-avatar">
                    <Navigation size={14} />
                  </div>
                  <div className="driver-details-wrap">
                    <h5>{d.full_name || `Driver #${d.driver_id}`}</h5>
                    <span>Raqam: {d.truck_number || "Yo'q"}</span>
                  </div>
                  <div className="driver-ping-time">
                    <Clock size={10} /> {new Date(d.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-sidebar">Faol haydovchilar topilmadi.</div>
            )}
          </div>
        </div>

        {/* MAP CONTAINER */}
        <div className="map-view-card glass-card">
          {errorMsg && <div className="map-error-banner">{errorMsg}</div>}
          <div ref={mapContainerRef} className="leaflet-map-element"></div>

          <div className="map-overlay-info">
            <Info size={14} />
            <span>Xaritada haydovchilar joylashuvi real-vaqtda (WebSocket orqali) yangilanadi.</span>
          </div>
        </div>
      </div>

      <style>{`
        .live-tracking-page {
          height: calc(100vh - var(--header-height) - 60px);
        }

        .tracking-layout {
          display: grid;
          grid-template-columns: 280px 1fr;
          gap: 20px;
          height: 100%;
        }

        @media (max-width: 768px) {
          .tracking-layout {
            grid-template-columns: 1fr;
            grid-template-rows: 200px 1fr;
          }
        }

        /* Drivers Sidebar */
        .drivers-sidebar {
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 16px;
          overflow: hidden;
        }

        .sidebar-header-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          border-bottom: 1px solid var(--border-color);
          padding-bottom: 12px;
        }

        .sidebar-header-row h4 {
          font-size: 14px;
          font-weight: 700;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .ws-status {
          font-size: 10px;
          font-weight: 700;
          padding: 4px 8px;
          border-radius: 9999px;
          display: flex;
          align-items: center;
          gap: 4px;
          text-transform: uppercase;
        }

        .ws-status.online {
          background: rgba(0, 230, 118, 0.15);
          color: #b9f6ca;
          border: 1px solid rgba(0, 230, 118, 0.3);
        }

        .ws-status.connecting {
          background: rgba(255, 179, 0, 0.15);
          color: #ffe57f;
          border: 1px solid rgba(255, 179, 0, 0.3);
        }

        .ws-status.offline {
          background: rgba(255, 23, 68, 0.15);
          color: #ff8a80;
          border: 1px solid rgba(255, 23, 68, 0.3);
        }

        .pulsing-icon {
          animation: ws-pulse 1.5s infinite ease-in-out;
        }

        @keyframes ws-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.85); }
        }

        .drivers-list {
          flex: 1;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 8px;
          padding-right: 4px;
        }

        .driver-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 12px;
          border-radius: var(--border-radius);
          background: rgba(255, 255, 255, 0.015);
          border: 1px solid transparent;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .driver-item:hover {
          background: rgba(255, 255, 255, 0.04);
          border-color: var(--border-color-hover);
        }

        .driver-item.selected {
          background: rgba(88, 101, 242, 0.1);
          border-color: rgba(88, 101, 242, 0.3);
        }

        .driver-avatar {
          width: 32px;
          height: 32px;
          border-radius: 8px;
          background: rgba(0, 210, 255, 0.1);
          color: var(--accent-secondary);
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .driver-details-wrap {
          flex: 1;
          min-width: 0;
        }

        .driver-details-wrap h5 {
          font-size: 13px;
          font-weight: 600;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .driver-details-wrap span {
          display: block;
          font-size: 10px;
          color: var(--text-muted);
        }

        .driver-ping-time {
          font-size: 10px;
          color: var(--text-muted);
          white-space: nowrap;
          display: flex;
          align-items: center;
          gap: 2px;
        }

        .empty-sidebar {
          text-align: center;
          padding: 40px 10px;
          font-size: 12px;
          color: var(--text-muted);
        }

        /* Map Card */
        .map-view-card {
          position: relative;
          padding: 6px;
          overflow: hidden;
          height: 100%;
        }

        .leaflet-map-element {
          width: 100%;
          height: 100%;
          z-index: 1;
        }

        .map-overlay-info {
          position: absolute;
          bottom: 20px;
          left: 20px;
          z-index: 5;
          background: rgba(10, 11, 16, 0.85);
          backdrop-filter: blur(8px);
          border: var(--glass-border);
          padding: 8px 16px;
          border-radius: 9999px;
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 11px;
          color: var(--text-secondary);
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .map-error-banner {
          position: absolute;
          top: 20px;
          left: 50%;
          transform: translateX(-50%);
          z-index: 5;
          background: rgba(255, 23, 68, 0.9);
          backdrop-filter: blur(8px);
          padding: 8px 16px;
          border-radius: var(--border-radius);
          font-size: 12px;
          font-weight: 600;
          color: white;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        /* Pop-up overrides styling */
        .popup-info h4 {
          font-size: 14px;
          font-weight: 700;
          margin-bottom: 6px;
          color: var(--text-primary);
        }

        .popup-info p {
          font-size: 12px;
          margin: 2px 0;
          color: var(--text-secondary);
        }
      `}</style>
    </div>
  );
};
