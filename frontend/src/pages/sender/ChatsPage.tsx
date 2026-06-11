import React, { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  CHAT_CATEGORY_LABELS,
  fetchMyChats,
} from "../../services/aiApi";
import type { ChatListItem, MessageStatus } from "../../types/ai";
import { MessageSquarePlus, CheckCheck, Check, Clock } from "lucide-react";

// ─── helpers ──────────────────────────────────────────────────────────────────

function formatRelativeTime(iso?: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const diffH = Math.floor(diffMin / 60);
  const diffD = Math.floor(diffH / 24);
  if (diffMin < 1) return "Hozir";
  if (diffMin < 60) return `${diffMin} daq`;
  if (diffH < 24) return `${diffH} soat`;
  if (diffD < 7) return `${diffD} kun`;
  return d.toLocaleDateString("uz-UZ", { month: "short", day: "numeric" });
}

function DeliveryIcon({ status }: { status?: MessageStatus }) {
  if (!status) return null;
  switch (status) {
    case "sending":   return <Clock size={11} className="status-icon sending" />;
    case "sent":      return <Check size={11} className="status-icon sent" />;
    case "delivered": return <CheckCheck size={11} className="status-icon delivered" />;
    case "read":      return <CheckCheck size={11} className="status-icon read" />;
    default:          return null;
  }
}

// ─── ChatsPage ─────────────────────────────────────────────────────────────────

export const ChatsPage: React.FC = () => {
  const [chats, setChats] = useState<ChatListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { pathname } = useLocation();
  const baseRoute = pathname.startsWith("/driver") ? "/driver" : "/sender";

  // Real-time unread badge update via global WS event bus
  useEffect(() => {
    const handler = (e: Event) => {
      const { chat_id } = (e as CustomEvent<{ chat_id: number }>).detail;
      setChats((prev) =>
        prev.map((c) =>
          c.id === chat_id
            ? { ...c, unread_count: c.unread_count + 1 }
            : c
        )
      );
    };
    window.addEventListener("ws:new_message", handler);
    return () => window.removeEventListener("ws:new_message", handler);
  }, []);

  // Peer presence updates
  useEffect(() => {
    const handler = (e: Event) => {
      const { chat_id, online } = (e as CustomEvent<{ chat_id: number; online: boolean; last_seen?: string }>).detail;
      setChats((prev) =>
        prev.map((c) =>
          c.id === chat_id
            ? { ...c, peer_online: online, peer_last_seen: online ? null : c.peer_last_seen }
            : c
        )
      );
    };
    window.addEventListener("ws:user_presence", handler);
    return () => window.removeEventListener("ws:user_presence", handler);
  }, []);

  useEffect(() => {
    let alive = true;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const data = await fetchMyChats();
        if (alive) setChats(data);
      } catch (ex: unknown) {
        if (alive) setError(ex instanceof Error ? ex.message : "Yuklanmadi");
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, []);

  const filtered = chats.filter((c) => c.category !== "ai_command");

  return (
    <div className="chats-page">
      {/* Header */}
      <div className="chats-header">
        <h2 className="chats-title">Chatlar</h2>
      </div>

      {error && <div className="mobile-alert mobile-alert-error">{error}</div>}
      {loading && (
        <div className="chats-skeleton">
          {[1, 2, 3].map((i) => (
            <div key={i} className="chat-skeleton-item">
              <div className="skeleton-avatar" />
              <div className="skeleton-lines">
                <div className="skeleton-line short" />
                <div className="skeleton-line long" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div className="chats-empty">
          <MessageSquarePlus size={40} strokeWidth={1.2} />
          <p>Hali chat yo'q.</p>
          <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
            Buyurtmani qabul qilgandan keyin chat avtomatik ochiladi.
          </p>
        </div>
      )}

      <ul className="chats-list">
        {filtered.map((chat) => {
          const lastMsg = chat.last_message;
          const isMyMsg = lastMsg && lastMsg.sender_type !== "ai";
          return (
            <li key={chat.id}>
              <Link
                to={`${baseRoute}/chats/${chat.id}`}
                className="chat-list-item"
                onClick={() =>
                  setChats((prev) =>
                    prev.map((c) => (c.id === chat.id ? { ...c, unread_count: 0 } : c))
                  )
                }
              >
                {/* Avatar with presence dot */}
                <div className="chat-avatar-wrap">
                  <div className="chat-avatar">
                    {(chat.title ?? `#${chat.id}`)[0]?.toUpperCase()}
                  </div>
                  {chat.peer_online && <span className="presence-dot" />}
                </div>

                {/* Content */}
                <div className="chat-item-body">
                  <div className="chat-item-top">
                    <span className="chat-item-title">
                      {chat.title ?? `Chat #${chat.id}`}
                    </span>
                    <span className="chat-item-time">
                      {formatRelativeTime(lastMsg?.created_at ?? chat.updated_at)}
                    </span>
                  </div>

                  <div className="chat-item-bottom">
                    <span className="chat-item-preview">
                      {isMyMsg && <DeliveryIcon status={lastMsg?.status} />}
                      {lastMsg?.is_deleted
                        ? <em style={{ color: "var(--text-muted)" }}>Xabar o'chirildi</em>
                        : lastMsg?.content ?? (
                            lastMsg?.attachments?.length
                              ? "📎 Fayl"
                              : <em style={{ color: "var(--text-muted)" }}>Xabar yo'q</em>
                          )
                      }
                    </span>
                    {chat.unread_count > 0 && (
                      <span className="unread-badge">
                        {chat.unread_count > 99 ? "99+" : chat.unread_count}
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
};
