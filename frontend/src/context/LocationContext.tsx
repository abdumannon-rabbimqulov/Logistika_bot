import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { useAuth } from "./AuthContext";
import { useDriverWebSocket } from "../hooks/useDriverWebSocket";

const STORAGE_KEY = "logistika_gps_enabled";
const SEND_INTERVAL_MS = 30_000;

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

export const LocationProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const isDriver = user?.role === "driver";

  const [enabled, setEnabledState] = useState(() => sessionStorage.getItem(STORAGE_KEY) === "1");
  const [gpsSessionActive, setGpsSessionActive] = useState(false);
  const [coords, setCoords] = useState<Coords | null>(null);
  const [gpsError, setGpsError] = useState<string | null>(null);

  const watchIdRef = useRef<number | null>(null);
  const sendIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const coordsRef = useRef<Coords | null>(null);
  coordsRef.current = coords;

  const wsEnabled = enabled && isDriver && gpsSessionActive;

  const { active, error: wsError, send } = useDriverWebSocket({
    enabled: wsEnabled,
    onOpen: () => {
      flushCoordsToServer();
    },
    onMessage: (data) => {
      const msg = data as { status?: string };
      if (msg.status === "connected" || msg.status === "acknowledged") {
        setGpsError(null);
      }
    },
  });

  const clearSendInterval = () => {
    if (sendIntervalRef.current != null) {
      clearInterval(sendIntervalRef.current);
      sendIntervalRef.current = null;
    }
  };

  const flushCoordsToServer = () => {
    const c = coordsRef.current;
    if (!c) return;
    send({ latitude: c.latitude, longitude: c.longitude });
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

  const stopGpsSession = () => {
    setGpsSessionActive(false);

    if (watchIdRef.current != null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }

    clearSendInterval();
  };

  const startGpsSession = () => {
    if (gpsSessionActive) return;
    if (!navigator.geolocation) {
      setGpsError("Geolokatsiya qo'llab-quvvatlanmaydi");
      return;
    }

    setGpsSessionActive(true);

    const onPosition = (position: GeolocationPosition) => {
      const next = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
      };
      coordsRef.current = next;
      setCoords(next);
    };

    const onError = (err: GeolocationPositionError) => {
      setGpsError(err.message || "GPS xatolik");
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
  };

  useEffect(() => {
    if (active) {
      startSendInterval();
    } else {
      clearSendInterval();
    }
    return () => clearSendInterval();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  /** GPS: faqat enabled / isDriver o'zgarganda */
  useEffect(() => {
    if (!isDriver || !enabled) {
      sessionStorage.removeItem(STORAGE_KEY);
      stopGpsSession();
      setCoords(null);
      setGpsError(null);
      return;
    }

    sessionStorage.setItem(STORAGE_KEY, "1");
    startGpsSession();

    return () => {
      stopGpsSession();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, isDriver]);

  const setEnabled = useCallback((on: boolean) => {
    setEnabledState(on);
  }, []);

  const toggle = useCallback(() => {
    setEnabledState((v) => !v);
  }, []);

  const error = gpsError ?? wsError;

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
