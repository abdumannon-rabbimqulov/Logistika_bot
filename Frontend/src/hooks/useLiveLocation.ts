import { useEffect, useRef, useState } from 'react';
import { getAccessToken, apiBaseUrl } from '../api/client';
import { getTelegramLocationOnce, isTelegramLocationSupported } from '../utils/telegramLocation';

export interface LiveCoords {
  latitude: number;
  longitude: number;
  accuracy: number | null;
  at: number;
}

interface Options {
  /** Liniyaga chiqqanda `true` — koordinata backendga (WS) ham yuboriladi. */
  broadcast?: boolean;
}

/**
 * Backendga yuborish oralig'i. Xaritadagi ko'k nuqta har bir GPS o'zgarishida
 * darhol yangilanadi, serverga esa 30 soniyada bir marta yuboriladi — mobil
 * trafik va Redis yozuvlarini tejaydi.
 */
const BROADCAST_INTERVAL_MS = 30_000;

/** Telegram `LocationManager`da `watchPosition` yo'q — shu oraliqda `getLocation()`
 *  qayta so'raladi. Xaritadagi nuqta shuncha tez-tez yangilanadi. */
const TELEGRAM_POLL_INTERVAL_MS = 8_000;

interface LiveLocationState {
  coords: LiveCoords | null;
  error: string | null;
  /** Birinchi koordinata hali kelmagan holat (xaritada "aniqlanmoqda" ko'rsatish uchun). */
  loading: boolean;
}

/** `/drivers/ws/location` manzilini quradi (client.ts dagi `driverLocationsWsUrl` naqshi). */
function locationWsUrl(): string {
  const base = apiBaseUrl().replace(/\/$/, '');
  let httpBase: string;
  try {
    httpBase = new URL(base, window.location.origin).toString().replace(/\/$/, '');
  } catch {
    httpBase = `${window.location.origin}${base}`;
  }
  const wsBase = httpBase.replace(/^http/, 'ws');
  return `${wsBase}/drivers/ws/location?token=${encodeURIComponent(getAccessToken() ?? '')}`;
}

/**
 * Haydovchining jonli joylashuvi va (broadcast=true bo'lsa) uni
 * `/drivers/ws/location` WebSocket'iga yuborish — admin/sender jonli xaritasi
 * aynan shu ma'lumotdan oziqlanadi (services/live_location.py).
 *
 * Joylashuv manbai: Telegram ichida (WebApp) `LocationManager` mavjud bo'lsa
 * ustuvor ishlatiladi — oddiy `navigator.geolocation` Telegram'ning ichki
 * WebView'ida (ayniqsa Android/iOS ilovasida) ko'pincha ishlamaydi: OS ruxsat
 * so'rovi umuman ko'rinmay doimiy `PERMISSION_DENIED` qaytaradi, chunki ruxsat
 * brauzerga emas, Telegram ilovasining o'ziga berilishi kerak
 * (`utils/telegramLocation.ts`). `LocationManager`da uzluksiz "watch" bo'lmagani
 * uchun davriy so'rov (`TELEGRAM_POLL_INTERVAL_MS`) bilan simulyatsiya qilinadi.
 * Telegramdan tashqarida (dev/test brauzerida) `watchPosition` ishlatiladi.
 *
 * Liniyadan chiqilganda WS'ga `{event: "stop"}` yuboriladi, shunda haydovchi admin
 * xaritasidan olib tashlanadi.
 */
export function useLiveLocation({ broadcast = false }: Options = {}): LiveLocationState {
  const [coords, setCoords] = useState<LiveCoords | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const socketRef = useRef<WebSocket | null>(null);
  // Oxirgi olingan koordinata — interval taymeri shu qiymatni yuboradi.
  const latestCoordsRef = useRef<LiveCoords | null>(null);

  // 1) Joylashuvni kuzatish (Telegram LocationManager yoki brauzer watchPosition).
  useEffect(() => {
    let cancelled = false;

    const applyCoords = (next: LiveCoords) => {
      if (cancelled) return;
      latestCoordsRef.current = next;
      setCoords(next);
      setError(null);
      setLoading(false);
    };

    if (isTelegramLocationSupported()) {
      const poll = () => {
        getTelegramLocationOnce()
          .then((sample) => {
            applyCoords({ ...sample, at: Date.now() });
          })
          .catch((err: unknown) => {
            if (cancelled) return;
            setError(err instanceof Error ? err.message : 'Joylashuv aniqlanmadi');
            setLoading(false);
          });
      };
      poll();
      const id = window.setInterval(poll, TELEGRAM_POLL_INTERVAL_MS);
      return () => {
        cancelled = true;
        window.clearInterval(id);
      };
    }

    if (!navigator.geolocation) {
      setError("Qurilma geolokatsiyani qo'llab-quvvatlamaydi");
      setLoading(false);
      return;
    }

    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        applyCoords({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy ?? null,
          at: Date.now(),
        });
      },
      (err) => {
        if (cancelled) return;
        setError(
          err.code === err.PERMISSION_DENIED
            ? "Joylashuvga ruxsat berilmagan — xaritada o'zingizni ko'rish uchun ruxsat bering"
            : 'Joylashuv aniqlanmadi',
        );
        setLoading(false);
      },
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 },
    );

    return () => {
      cancelled = true;
      navigator.geolocation.clearWatch(watchId);
    };
  }, []);

  // 2) Liniyadagi holatda — WS ulanishi
  useEffect(() => {
    if (!broadcast) return;

    let closedByUs = false;
    let socket: WebSocket;
    try {
      socket = new WebSocket(locationWsUrl());
    } catch {
      return; // WS ochilmasa xaritadagi ko'rsatish baribir ishlaydi
    }
    socketRef.current = socket;

    return () => {
      closedByUs = true;
      socketRef.current = null;
      try {
        if (socket.readyState === WebSocket.OPEN) {
          // Liniyadan chiqdik — admin xaritasidan ham olib tashlansin
          socket.send(JSON.stringify({ event: 'stop' }));
        }
        socket.close();
      } catch {
        // ulanish allaqachon yopilgan
      }
      void closedByUs;
    };
  }, [broadcast]);

  // 3) Koordinatani backendga har 30 soniyada yuborish.
  //    `watchPosition` sekundiga bir necha marta ishga tushishi mumkin — har birini
  //    yuborish ortiqcha; shuning uchun eng oxirgi koordinata taymer bo'yicha ketadi.
  useEffect(() => {
    if (!broadcast) return;

    const send = () => {
      const socket = socketRef.current;
      const point = latestCoordsRef.current;
      if (!socket || !point) return;
      if (socket.readyState !== WebSocket.OPEN) return;

      // `accuracy` ham yuboriladi: server geofence tekshiruvida zaxira koordinata
      // sifatida shu nuqtadan foydalanganda ruxsat etilgan radiusni aniqlikka qarab
      // kengaytiradi (services/geofence.py).
      socket.send(
        JSON.stringify({
          latitude: point.latitude,
          longitude: point.longitude,
          ...(point.accuracy != null ? { accuracy: point.accuracy } : {}),
        }),
      );
    };

    // Birinchi koordinata kelishi bilan darhol yuboriladi (30s kutilmaydi), keyin interval.
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.CONNECTING) {
      socket.addEventListener('open', send, { once: true });
    } else {
      send();
    }

    const timer = window.setInterval(send, BROADCAST_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [broadcast, coords !== null]);

  return { coords, error, loading };
}
