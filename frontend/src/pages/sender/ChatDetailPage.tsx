import React, { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { CHAT_CATEGORY_LABELS, fetchChat, fetchChatMessages } from "../../services/aiApi";
import type { Chat, ChatMessage } from "../../types/ai";
import { useAuth } from "../../context/AuthContext";
import { getWebSocketUrl } from "../../api";
import { Send } from "lucide-react";

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("uz-UZ", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "";
  }
}

export const ChatDetailPage: React.FC = () => {
  const { chatId } = useParams<{ chatId: string }>();
  const id = Number(chatId);

  const { user } = useAuth();

  const [chat, setChat] = useState<Chat | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [input, setInput] = useState("");

  const [ws, setWs] = useState<WebSocket | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollDown = () => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // 1. Initial Load of Chat Details & Message History
  useEffect(() => {
    if (!id || Number.isNaN(id)) return;
    setLoading(true);
    setError("");
    Promise.all([fetchChat(id), fetchChatMessages(id, { limit: 50 })])
      .then(([c, msgs]) => {
        setChat(c);
        setMessages(msgs.sort((a, b) => a.id - b.id));
      })
      .catch((ex: unknown) => setError(ex instanceof Error ? ex.message : "Yuklanmadi"))
      .finally(() => setLoading(false));
  }, [id]);

  // 2. Establish WebSocket Connection
  useEffect(() => {
    if (!id || Number.isNaN(id) || loading || !chat) return;

    const token = localStorage.getItem("logistika_access_token");
    if (!token) return;

    const wsUrl = getWebSocketUrl(`/ai/ws/${id}?token=${token}`);
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      setWsConnected(true);
      console.log(`WebSocket connected to chat ${id}`);
    };

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.event === "new_message") {
          const newMsg = payload.data;
          setMessages((prev) => {
            if (prev.some((m) => m.id === newMsg.id)) return prev;
            return [...prev, newMsg];
          });
        } else if (payload.event === "connected") {
          if (payload.data?.messages) {
            setMessages((prev) => {
              const merged = [...prev];
              payload.data.messages.forEach((m: ChatMessage) => {
                if (!merged.some((existing) => existing.id === m.id)) {
                  merged.push(m);
                }
              });
              return merged.sort((a, b) => a.id - b.id);
            });
          }
        }
      } catch (err) {
        console.error("WS parse error:", err);
      }
    };

    socket.onclose = () => {
      setWsConnected(false);
      console.log(`WebSocket disconnected from chat ${id}`);
    };

    setWs(socket);

    return () => {
      socket.close();
    };
  }, [id, loading, chat]);

  // 3. Scroll down on new message
  useEffect(() => {
    scrollDown();
  }, [messages]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;

    ws.send(
      JSON.stringify({
        type: "new_message",
        content: text,
      })
    );
    setInput("");
  };

  if (loading) return <p className="ai-chat-empty">Chat yuklanmoqda...</p>;
  if (error) return <div className="mobile-alert mobile-alert-error">{error}</div>;
  if (!chat) return <p className="ai-chat-empty">Chat topilmadi</p>;

  return (
    <div className="ai-chat-page">
      <div className="mobile-card" style={{ margin: "12px 16px 4px 16px" }}>
        <h3 style={{ margin: "0 0 4px", fontSize: "15px", fontWeight: 600 }}>
          {chat.title || `Chat #${chat.id}`}
        </h3>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <p style={{ fontSize: "12px", color: "var(--text-secondary)", margin: 0 }}>
            {CHAT_CATEGORY_LABELS[chat.category] ?? chat.category} · {chat.status}
          </p>
          <span
            style={{
              fontSize: "10px",
              padding: "2px 6px",
              borderRadius: "4px",
              background: wsConnected ? "rgba(34, 197, 94, 0.2)" : "rgba(239, 68, 68, 0.2)",
              color: wsConnected ? "#4ade80" : "#f87171",
              fontWeight: 500,
            }}
          >
            {wsConnected ? "Online" : "Connecting..."}
          </span>
        </div>
        {chat.order_id && (
          <p style={{ fontSize: "11px", marginTop: "4px", color: "var(--text-muted)", margin: "4px 0 0" }}>
            Buyurtma ID: {chat.order_id}
          </p>
        )}
      </div>

      <div className="ai-chat-messages">
        {messages.length === 0 && (
          <p className="ai-chat-empty">Suhbatni boshlash uchun birinchi xabarni yozing.</p>
        )}
        {messages.map((m) => {
          const isMe = m.sender_id === user?.id;
          const isSystem = m.sender_type === "system";
          const bubbleClass = isMe ? "user" : isSystem ? "system" : "ai";

          return (
            <div key={m.id} className={`ai-chat-bubble ${bubbleClass}`}>
              {!isMe && !isSystem && (
                <span style={{ display: "block", fontSize: "11px", color: "var(--text-muted)", marginBottom: "2px", fontWeight: 500 }}>
                  {m.sender_type === "driver" ? "Haydovchi" : "Mijoz"}
                </span>
              )}
              {m.content}
              <time>{formatTime(m.created_at)}</time>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      <form className="ai-chat-input-bar" onSubmit={handleSend}>
        <textarea
          rows={1}
          placeholder="Xabarni yozing..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend(e);
            }
          }}
          disabled={!wsConnected}
        />
        <button
          type="submit"
          className="ai-chat-send"
          disabled={!input.trim() || !wsConnected}
          aria-label="Yuborish"
        >
          <Send size={20} />
        </button>
      </form>
    </div>
  );
};
