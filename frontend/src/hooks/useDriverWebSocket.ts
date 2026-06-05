import { useCallback, useEffect, useRef, useState } from "react";
import { getWebSocketUrl, refreshAccessToken } from "../api";

const WS_PATH = "/drivers/ws/location";
const MIN_RECONNECT_MS = 3000;
const MAX_RECONNECT_MS = 30000;
const TOKEN_REFRESH_SKEW_SEC = 60;

const AUTH_CLOSE_CODES = new Set([4401, 4403, 1008]);

export interface UseDriverWebSocketOptions {
  enabled: boolean;
  onMessage?: (data: unknown) => void;
  onOpen?: () => void;
}

export interface UseDriverWebSocketResult {
  active: boolean;
  error: string | null;
  send: (payload: Record<string, unknown>) => boolean;
  disconnect: (sendStop?: boolean) => void;
}

function getAccessToken(): string {
  return (
    localStorage.getItem("logistika_access_token") ||
    localStorage.getItem("token") ||
    ""
  );
}

function isTokenExpiredOrSoon(token: string, skewSec = TOKEN_REFRESH_SKEW_SEC): boolean {
  try {
    const parts = token.split(".");
    if (parts.length < 2) return true;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/"))) as {
      exp?: number;
    };
    if (!payload.exp) return true;
    return Date.now() / 1000 >= payload.exp - skewSec;
  } catch {
    return true;
  }
}

async function ensureFreshAccessToken(forceRefresh = false): Promise<string> {
  const current = getAccessToken();
  if (!forceRefresh && current && !isTokenExpiredOrSoon(current)) {
    return current;
  }
  return refreshAccessToken();
}

function buildDriverLocationWsUrl(accessToken: string): string {
  const encoded = encodeURIComponent(accessToken);
  const isLocalDev =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1";

  if (isLocalDev) {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${window.location.host}/api${WS_PATH}?token=${encoded}`;
  }
  return `${getWebSocketUrl(WS_PATH)}?token=${encoded}`;
}

function isAuthClose(event: CloseEvent, openedSuccessfully: boolean): boolean {
  if (AUTH_CLOSE_CODES.has(event.code)) return true;

  const reason = (event.reason || "").toLowerCase();
  if (
    reason.includes("unauthorized") ||
    reason.includes("forbidden") ||
    reason.includes("token")
  ) {
    return true;
  }

  // Handshake 403 / token muammosi: ulanish ochilmay yopiladi
  if (!openedSuccessfully && (event.code === 1006 || event.code === 1002)) {
    return true;
  }

  return false;
}

function reconnectDelay(attempt: number): number {
  return Math.min(MIN_RECONNECT_MS * 2 ** attempt, MAX_RECONNECT_MS);
}

export function useDriverWebSocket({
  enabled,
  onMessage,
  onOpen,
}: UseDriverWebSocketOptions): UseDriverWebSocketResult {
  const [active, setActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const connectingRef = useRef(false);
  const intentionalCloseRef = useRef(false);
  const reconnectAttemptRef = useRef(0);
  const openedSuccessfullyRef = useRef(false);
  const enabledRef = useRef(enabled);

  const onMessageRef = useRef(onMessage);
  const onOpenRef = useRef(onOpen);
  onMessageRef.current = onMessage;
  onOpenRef.current = onOpen;
  enabledRef.current = enabled;

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const disconnect = useCallback(
    (sendStop = false) => {
      clearReconnectTimer();
      connectingRef.current = false;
      reconnectAttemptRef.current = 0;

      const ws = wsRef.current;
      if (!ws) {
        setActive(false);
        return;
      }

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
    },
    [clearReconnectTimer]
  );

  const connectInternalRef = useRef<(forceRefresh?: boolean) => Promise<void>>(async () => {});

  const scheduleReconnect = useCallback(
    (forceRefresh: boolean) => {
      if (!enabledRef.current || intentionalCloseRef.current) return;

      clearReconnectTimer();
      const attempt = reconnectAttemptRef.current;
      const delay = reconnectDelay(attempt);

      reconnectTimerRef.current = setTimeout(async () => {
        if (!enabledRef.current) return;

        try {
          await ensureFreshAccessToken(forceRefresh);
          reconnectAttemptRef.current = attempt + 1;
          await connectInternalRef.current(forceRefresh);
        } catch {
          setError("Sessiya muddati tugadi. Qayta kiring.");
          setActive(false);
        }
      }, delay);
    },
    [clearReconnectTimer]
  );

  const connectInternal = useCallback(
    async (forceRefresh = false): Promise<void> => {
      if (!enabledRef.current) return;
      if (connectingRef.current) return;
      if (wsRef.current?.readyState === WebSocket.OPEN) return;
      if (wsRef.current?.readyState === WebSocket.CONNECTING) return;

      connectingRef.current = true;
      openedSuccessfullyRef.current = false;

      try {
        const token = await ensureFreshAccessToken(forceRefresh);
        const url = buildDriverLocationWsUrl(token);
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
          connectingRef.current = false;
          openedSuccessfullyRef.current = true;
          reconnectAttemptRef.current = 0;

          if (!enabledRef.current) {
            disconnect(false);
            return;
          }

          setError(null);
          setActive(true);
          onOpenRef.current?.();
        };

        ws.onmessage = (ev) => {
          try {
            const data = JSON.parse(ev.data as string) as unknown;
            onMessageRef.current?.(data);
          } catch {
            /* ignore */
          }
        };

        ws.onerror = () => {
          connectingRef.current = false;
          if (enabledRef.current) {
            setError("WebSocket ulanishi xatolik");
          }
          setActive(false);
        };

        ws.onclose = (event) => {
          connectingRef.current = false;
          if (wsRef.current === ws) wsRef.current = null;
          setActive(false);

          if (intentionalCloseRef.current || !enabledRef.current) {
            return;
          }

          const authFailure = isAuthClose(event, openedSuccessfullyRef.current);
          scheduleReconnect(authFailure);
        };
      } catch (err: unknown) {
        connectingRef.current = false;
        const msg = err instanceof Error ? err.message : "Token yangilanmadi";
        setError(msg);
        setActive(false);
        scheduleReconnect(true);
      }
    },
    [disconnect, scheduleReconnect]
  );

  connectInternalRef.current = connectInternal;

  const send = useCallback((payload: Record<string, unknown>): boolean => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    try {
      ws.send(JSON.stringify(payload));
      return true;
    } catch {
      return false;
    }
  }, []);

  useEffect(() => {
    if (enabled) {
      reconnectAttemptRef.current = 0;
      void connectInternal(false);
    } else {
      disconnect(true);
      setError(null);
    }

    return () => {
      disconnect(true);
    };
  }, [enabled, connectInternal, disconnect]);

  return { active, error, send, disconnect };
}
