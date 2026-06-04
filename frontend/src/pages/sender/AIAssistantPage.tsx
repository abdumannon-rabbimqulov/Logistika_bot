import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  fetchAssistantChat,
  fetchAssistantMessages,
  fetchMyAiUsage,
  sendAssistantMessage,
} from "../../services/aiApi";
import type { ChatMessage } from "../../types/ai";
import { Send } from "lucide-react";

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("uz-UZ", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

export const AIAssistantPage: React.FC = () => {
  const [chatId, setChatId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [usage, setUsage] = useState<{ used: number; limit: number; allowed: boolean } | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollDown = () => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const loadChat = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [chat, usageData] = await Promise.all([fetchAssistantChat(), fetchMyAiUsage()]);
      setChatId(chat.id);
      setUsage({
        used: usageData.used_today,
        limit: usageData.daily_limit,
        allowed: usageData.allowed,
      });
      const msgs = await fetchAssistantMessages({ chat_id: chat.id, limit: 50 });
      setMessages(msgs);
    } catch (ex: unknown) {
      setError(ex instanceof Error ? ex.message : "Yuklanmadi");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadChat();
  }, [loadChat]);

  useEffect(() => {
    scrollDown();
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    setSending(true);
    setError("");
    setInput("");

    const optimistic: ChatMessage = {
      id: -Date.now(),
      chat_id: chatId ?? 0,
      sender_type: "user",
      message_type: "text",
      content: text,
      is_read: true,
      is_ai_response: false,
      is_ai_command: false,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);

    try {
      const res = await sendAssistantMessage(text, chatId ?? undefined);
      setChatId(res.chat_id);
      setUsage({ used: res.used_today, limit: res.daily_limit, allowed: res.allowed });

      const aiMsg: ChatMessage = {
        id: -Date.now() - 1,
        chat_id: res.chat_id,
        sender_type: "ai",
        message_type: "ai_reply",
        content: res.reply,
        is_read: true,
        is_ai_response: true,
        is_ai_command: false,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev.filter((m) => m.id !== optimistic.id), optimistic, aiMsg]);
    } catch (ex: unknown) {
      setMessages((prev) => prev.filter((m) => m.id !== optimistic.id));
      setInput(text);
      setError(ex instanceof Error ? ex.message : "Yuborilmadi");
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return <p className="ai-chat-empty">AI chat yuklanmoqda...</p>;
  }

  return (
    <div className="ai-chat-page">
      {usage && (
        <div className="ai-chat-usage">
          Bugun: {usage.used} / {usage.limit} so&apos;rov
          {!usage.allowed && " · Limit tugagan"}
        </div>
      )}

      {error && <div className="mobile-alert mobile-alert-error" style={{ margin: "8px 16px" }}>{error}</div>}

      <div className="ai-chat-messages">
        {messages.length === 0 && (
          <p className="ai-chat-empty">Logistika AI ga savol bering — buyurtma, yuk, haydovchi haqida.</p>
        )}
        {messages.map((m) => {
          const isUser = m.sender_type === "user";
          const isAi = m.sender_type === "ai" || m.is_ai_response;
          return (
            <div
              key={m.id}
              className={`ai-chat-bubble ${isUser ? "user" : isAi ? "ai" : "system"}`}
            >
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
          placeholder="Savolingizni yozing..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend(e);
            }
          }}
          disabled={sending || usage?.allowed === false}
        />
        <button
          type="submit"
          className="ai-chat-send"
          disabled={!input.trim() || sending || usage?.allowed === false}
          aria-label="Yuborish"
        >
          <Send size={20} />
        </button>
      </form>
    </div>
  );
};
