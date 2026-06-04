import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { CHAT_CATEGORY_LABELS, fetchChat, fetchChatMessages } from "../../services/aiApi";
import type { Chat, ChatMessage } from "../../types/ai";

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString("uz-UZ", {
      day: "2-digit",
      month: "2-digit",
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

  const [chat, setChat] = useState<Chat | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id || Number.isNaN(id)) return;
    setLoading(true);
    setError("");
    Promise.all([fetchChat(id), fetchChatMessages(id, { limit: 50 })])
      .then(([c, msgs]) => {
        setChat(c);
        setMessages(msgs);
      })
      .catch((ex: unknown) => setError(ex instanceof Error ? ex.message : "Yuklanmadi"))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <p className="ai-chat-empty">Chat yuklanmoqda...</p>;
  if (error) return <div className="mobile-alert mobile-alert-error">{error}</div>;
  if (!chat) return <p className="ai-chat-empty">Chat topilmadi</p>;

  return (
    <div>
      <div className="mobile-card" style={{ marginBottom: 12 }}>
        <p style={{ fontSize: 11, color: "var(--text-muted)", margin: "0 0 8px" }}>
          GET /ai/chats/{chat.id}
        </p>
        <h3 style={{ margin: "0 0 8px" }}>{chat.title || `Chat #${chat.id}`}</h3>
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: 0 }}>
          {CHAT_CATEGORY_LABELS[chat.category] ?? chat.category} · {chat.status}
        </p>
        {chat.order_id && (
          <p style={{ fontSize: 12, marginTop: 8, color: "var(--text-muted)" }}>
            Buyurtma ID: {chat.order_id}
          </p>
        )}
      </div>

      <h4 style={{ fontSize: 14, marginBottom: 10 }}>Xabarlar</h4>
      <div className="ai-chat-messages" style={{ maxHeight: "50vh", marginBottom: 12 }}>
        {messages.length === 0 && (
          <p className="ai-chat-empty">Xabarlar hali yo&apos;q</p>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`ai-chat-bubble ${m.sender_type === "user" ? "user" : m.sender_type === "ai" ? "ai" : "system"}`}
          >
            {m.content}
            <time>{formatTime(m.created_at)}</time>
          </div>
        ))}
      </div>

      <p style={{ fontSize: 12, color: "var(--text-muted)", textAlign: "center" }}>
        Real vaqtda yozish: WebSocket /ai/ws/{chat.id}
      </p>
    </div>
  );
};
