import { useEffect, useRef, useState } from 'react';
import { getOrderDriverLocation, orderDriverLocationWsUrl } from '../api/orders';

export interface OrderDriverPoint {
  latitude: number;
  longitude: number;
  accuracy: number | null;
  at: number;
}

interface WsPayload {
  event: 'snapshot' | 'update' | 'no_driver';
  item?: { lat: number; lon: number; accuracy: number | null; stopped?: boolean } | null;
}

/**
 * Sender ekranida biriktirilgan haydovchining jonli joylashuvi — `order/router.py`
 * `WS /orders/{id}/ws/driver-location` orqali (admin xaritasidagi manba bilan bir xil
 * Redis pub/sub, lekin faqat shu buyurtmaning haydovchisi bo'yicha filtrlangan).
 *
 * WS ochilmasa (masalan eski brauzer yoki tarmoq to'sig'i) `GET .../driver-location`
 * bilan har 10 soniyada so'raladigan zaxira rejimga o'tadi — xarita baribir ishlaydi,
 * faqat yangilanish kamroq tez-tez bo'ladi.
 */
export function useOrderDriverLocation(orderId: number | null, enabled: boolean) {
  const [point, setPoint] = useState<OrderDriverPoint | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!enabled || !orderId) {
      setPoint(null);
      return;
    }

    let cancelled = false;
    let pollTimer: number | null = null;

    const applyItem = (item: WsPayload['item']) => {
      if (cancelled || !item || item.stopped) return;
      setPoint({ latitude: item.lat, longitude: item.lon, accuracy: item.accuracy, at: Date.now() });
    };

    const startPolling = () => {
      if (pollTimer != null) return;
      const poll = () => {
        getOrderDriverLocation(orderId)
          .then((loc) => {
            if (!cancelled) {
              setPoint({ latitude: loc.lat, longitude: loc.lon, accuracy: loc.accuracy, at: Date.now() });
            }
          })
          .catch(() => {
            // haydovchi hali jonli translyatsiya qilmayotgan bo'lishi mumkin — jim kutamiz
          });
      };
      poll();
      pollTimer = window.setInterval(poll, 10_000);
    };

    let socket: WebSocket;
    try {
      socket = new WebSocket(orderDriverLocationWsUrl(orderId));
    } catch {
      startPolling();
      return () => {
        cancelled = true;
        if (pollTimer != null) window.clearInterval(pollTimer);
      };
    }
    socketRef.current = socket;

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string) as WsPayload;
        if (data.event === 'snapshot' || data.event === 'update') applyItem(data.item);
      } catch {
        // jim — keyingi xabar kutiladi
      }
    };
    socket.onerror = () => {
      startPolling();
    };
    socket.onclose = () => {
      startPolling();
    };

    return () => {
      cancelled = true;
      socketRef.current = null;
      if (pollTimer != null) window.clearInterval(pollTimer);
      try {
        socket.close();
      } catch {
        // allaqachon yopilgan
      }
    };
  }, [orderId, enabled]);

  return point;
}
