import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { getWebSocketUrl } from "../api";
import { useAuth } from "./AuthContext";

const STORAGE_KEY = "logistika_gps_enabled";
const SEND_INTERVAL_MS = 30_000;
const WS_PATH = "/drivers/ws/location";
const RECONNECT_MS = 5000;

interface Coords {
  latitude: number;
  longitude: number;
}

interface LocationContextValue {
  enabled: boolean;
  active: boolean;
  coords: Coords | null;
  error: string | null;
  setEnabled: (on: boolean) => void;
  toggle: () => void;
}

const LocationContext = createContext<LocationContextValue | null>(null);

function getAccessToken(): string {
  return (
    localStorage.getItem("logistika_access_token") ||
    localStorage.getItem("token") ||
    ""
  );
}

function buildDriverLocationWsUrl(): string | null {
  const token = getAccessToken();
  if (!token) return null;

  const encoded = encodeURIComponent(token);
  const isLocalDev =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1";

  if (isLocalDev) {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${window.location.host}/api${WS_PATH}?token=${encoded}`;
  }
  return `${getWebSocketUrl(WS_PATH)}?token=${encoded}`;
}

export const LocationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const isDriver = user?.role === "driver";

  const [enabled, setEnabledState] = useState(() => sessionStorage.getItem(STORAGE_KEY) === "1");
  const [active, setActive] = useState(false);
  const [coords, setCoords] = useState<Coords | null>(null);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const watchIdRef = useRef<number | null>(null);
  const sendIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectingRef = useRef(false);
  const intentionalCloseRef = useRef(false);
  const gpsSessionActiveRef = useRef(false);
  const coordsRef = useRef<Coords | null>(null);

  const enabledRef = useRef(enabled);
  const isDriverRef = useRef(isDriver);
  enabledRef.current = enabled;
  isDriverRef.current = isDriver;
  coordsRef.current = coords;

  const clearReconnectTimer = () => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  };

  const clearSendInterval = () => {
    if (sendIntervalRef.current != null) {
      clearInterval(sendIntervalRef.current);
      sendIntervalRef.current = null;
    }
  };

  const flushCoordsToServer = () => {
    const ws = wsRef.current;
    const c = coordsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || !c) return;
    ws.send(JSON.stringify({ latitude: c.latitude, longitude: c.longitude }));
  };

  const startSendInterval = () => {
    clearSendInterval();
    flushCoordsToServer();
    sendIntervalRef.current = setInterval(() => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const next = {
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
          };
          coordsRef.current = next;
          setCoords(next);
          flushCoordsToServer();
        },
        () => flushCoordsToServer(),
        { enableHighAccuracy: true, maximumAge: SEND_INTERVAL_MS, timeout: 15_000 }
      );
    }, SEND_INTERVAL_MS);
  };

  const closeSocket = (sendStop = false) => {
    clearSendInterval();
    clearReconnectTimer();
    connectingRef.current = false;
    const ws = wsRef.current;
    if (!ws) return;

    intentionalCloseRef.current = true;
    if (sendStop && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify({ event: "stop" }));
      } catch {
        /* ignore */
      }
    }
    wsRef.current = null;
    ws.close();
    intentionalCloseRef.current = false;
    setActive(false);
  };

  const openWebSocket = () => {
    if (!enabledRef.current || !isDriverRef.current) return;
    if (connectingRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return;

    const url = buildDriverLocationWsUrl();
    if (!url) {
      setError("Avtorizatsiya tokeni topilmadi");
      return;
    }

    connectingRef.current = true;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      connectingRef.current = false;
      if (!enabledRef.current) {
        intentionalCloseRef.current = true;
        ws.close();
        intentionalCloseRef.current = false;
        return;
      }
      setError(null);
      setActive(true);
      startSendInterval();
    };

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data as string) as { status?: string };
        if (data.status === "connected" || data.status === "acknowledged") {
          setActive(true);
          setError(null);
        }
      } catch {
        /* ignore */
      }
    };

    ws.onerror = () => {
      connectingRef.current = false;
      clearSendInterval();
      if (enabledRef.current) setError("WebSocket ulanishi xatolik");
      setActive(false);
    };

    ws.onclose = () => {
      connectingRef.current = false;
      clearSendInterval();
      if (wsRef.current === ws) wsRef.current = null;
      setActive(false);

      if (intentionalCloseRef.current || !enabledRef.current || !gpsSessionActiveRef.current) {
        return;
      }

      clearReconnectTimer();
      reconnectTimerRef.current = setTimeout(() => {
        if (enabledRef.current && gpsSessionActiveRef.current) {
          openWebSocket();
        }
      }, RECONNECT_MS);
    };
  };

  const stopGpsSession = (sendStop = false) => {
    gpsSessionActiveRef.current = false;

    if (watchIdRef.current != null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }

    closeSocket(sendStop);
  };

  const startGpsSession = () => {
    if (gpsSessionActiveRef.current) return;
    if (!navigator.geolocation) {
      setError("Geolokatsiya qo'llab-quvvatlanmaydi");
      return;
    }

    gpsSessionActiveRef.current = true;

    const onPosition = (position: GeolocationPosition) => {
      const next = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
      };
      coordsRef.current = next;
      setCoords(next);

      const state = wsRef.current?.readyState;
      if (state !== WebSocket.OPEN && state !== WebSocket.CONNECTING) {
        openWebSocket();
      }
    };

    const onError = (err: GeolocationPositionError) => {
      setError(err.message || "GPS xatolik");
    };

    navigator.geolocation.getCurrentPosition(onPosition, onError, {
      enableHighAccuracy: true,
      timeout: 15_000,
    });

    watchIdRef.current = navigator.geolocation.watchPosition(onPosition, onError, {
      enableHighAccuracy: true,
      maximumAge: SEND_INTERVAL_MS,
      timeout: 20_000,
    });

    openWebSocket();
  };

  /** GPS: faqat enabled / isDriver o'zgarganda — bitta mount/unmount tsikli */
  useEffect(() => {
    if (!isDriver || !enabled) {
      sessionStorage.removeItem(STORAGE_KEY);
      stopGpsSession(true);
      setCoords(null);
      setError(null);
      return;
    }

    sessionStorage.setItem(STORAGE_KEY, "1");
    startGpsSession();

    return () => {
      stopGpsSession(true);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, isDriver]);

  const setEnabled = useCallback((on: boolean) => {
    setEnabledState(on);
  }, []);

  const toggle = useCallback(() => {
    setEnabledState((v) => !v);
  }, []);

  return (
    <LocationContext.Provider value={{ enabled, active, coords, error, setEnabled, toggle }}>
      {children}
    </LocationContext.Provider>
  );
};

export function useLocation(): LocationContextValue {
  const ctx = useContext(LocationContext);
  if (!ctx) throw new Error("useLocation requires LocationProvider");
  return ctx;
}
