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
import { fetchDriverMe } from "../services/driverApi";

const STORAGE_KEY = "logistika_gps_enabled";
/** Serverga koordinata yuborish intervali (ms) */
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

/** Dev: Vite proxy orqali; prod: API host. */
export function buildDriverLocationWsUrl(): string | null {
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
  /** Faqat WS ochiq bo'lganda: serverga har 30 s yuborish */
  const sendIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const driverIdRef = useRef<number | null>(null);
  const enabledRef = useRef(enabled);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectingRef = useRef(false);
  const mountedRef = useRef(true);
  const coordsRef = useRef<Coords | null>(null);

  enabledRef.current = enabled;
  coordsRef.current = coords;

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  /** WebSocket yuborish intervalini to'xtatish (onclose / unmount) */
  const clearSendInterval = useCallback(() => {
    if (sendIntervalRef.current != null) {
      clearInterval(sendIntervalRef.current);
      sendIntervalRef.current = null;
    }
  }, []);

  /** Joriy koordinatalarni serverga yuborish — faqat WS OPEN */
  const flushCoordsToServer = useCallback(() => {
    const ws = wsRef.current;
    const c = coordsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || !c) return;

    ws.send(
      JSON.stringify({
        latitude: c.latitude,
        longitude: c.longitude,
      })
    );
  }, []);

  /** WS onopen dan keyin: darhol 1 marta + har 30 s */
  const startSendInterval = useCallback(() => {
    clearSendInterval();
    flushCoordsToServer();

    sendIntervalRef.current = setInterval(() => {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const { latitude, longitude } = pos.coords;
          const next = { latitude, longitude };
          coordsRef.current = next;
          setCoords(next);
          flushCoordsToServer();
        },
        () => flushCoordsToServer(),
        { enableHighAccuracy: true, maximumAge: SEND_INTERVAL_MS, timeout: 15_000 }
      );
    }, SEND_INTERVAL_MS);
  }, [clearSendInterval, flushCoordsToServer]);

  const closeSocket = useCallback(
    (sendStop = false) => {
      clearSendInterval();
      clearReconnectTimer();
      connectingRef.current = false;
      const ws = wsRef.current;
      if (!ws) return;

      if (sendStop && ws.readyState === WebSocket.OPEN) {
        try {
          ws.send(JSON.stringify({ event: "stop" }));
        } catch {
          /* ignore */
        }
      }
      wsRef.current = null;
      ws.close();
      setActive(false);
    },
    [clearSendInterval, clearReconnectTimer]
  );

  const openWebSocket = useCallback(() => {
    if (!enabledRef.current || !isDriver || connectingRef.current) return;
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
        ws.close();
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
      if (!enabledRef.current || !mountedRef.current) return;

      clearReconnectTimer();
      reconnectTimerRef.current = setTimeout(() => {
        if (enabledRef.current) openWebSocket();
      }, RECONNECT_MS);
    };
  }, [isDriver, clearSendInterval, clearReconnectTimer, startSendInterval]);

  const stopTracking = useCallback(() => {
    if (watchIdRef.current != null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
    clearSendInterval();
    closeSocket(true);
  }, [clearSendInterval, closeSocket]);

  const startTracking = useCallback(() => {
    if (!navigator.geolocation) {
      setError("Geolokatsiya qo'llab-quvvatlanmaydi");
      return;
    }

    openWebSocket();

    const onPosition = (position: GeolocationPosition) => {
      const { latitude, longitude } = position.coords;
      const next = { latitude, longitude };
      coordsRef.current = next;
      setCoords(next);
      if (wsRef.current?.readyState !== WebSocket.OPEN) {
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
  }, [openWebSocket]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!isDriver || !enabled) {
      sessionStorage.removeItem(STORAGE_KEY);
      stopTracking();
      setCoords(null);
      setError(null);
      driverIdRef.current = null;
      return;
    }

    sessionStorage.setItem(STORAGE_KEY, "1");

    fetchDriverMe()
      .then((me) => {
        driverIdRef.current = me.id;
      })
      .catch(() => {});

    startTracking();

    return () => {
      stopTracking();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- faqat enable/rol o'zgarganda
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
