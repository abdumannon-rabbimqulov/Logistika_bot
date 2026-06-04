import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  CHAT_CATEGORY_LABELS,
  createChat,
  fetchMyChats,
} from "../../services/aiApi";
import type { Chat, ChatCategory } from "../../types/ai";
import { MessageSquarePlus, ChevronRight } from "lucide-react";

const CATEGORIES: ChatCategory[] = ["conversation", "complaint", "suggestion", "support"];

export const ChatsPage: React.FC = () => {
  const [chats, setChats] = useState<Chat[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState<ChatCategory>("conversation");
  const [creating, setCreating] = useState(false);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setChats(await fetchMyChats());
    } catch (ex: unknown) {
      setError(ex instanceof Error ? ex.message : "Yuklanmadi");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError("");
    try {
      await createChat({ category, title: title.trim() || null });
      setShowCreate(false);
      setTitle("");
      setCategory("conversation");
      await load();
    } catch (ex: unknown) {
      setError(ex instanceof Error ? ex.message : "Yaratilmadi");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div>
      <div className="ai-chat-toolbar">
        <h3 style={{ margin: 0, fontSize: 16 }}>Mening chatlarim</h3>
        <button type="button" className="btn btn-primary" onClick={() => setShowCreate(!showCreate)}>
          <MessageSquarePlus size={18} /> Yangi
        </button>
      </div>

      {error && <div className="mobile-alert mobile-alert-error">{error}</div>}

      {showCreate && (
        <form className="ai-chat-create-form" onSubmit={handleCreate}>
          <p style={{ fontSize: 12, color: "var(--text-muted)", margin: 0 }}>POST /ai/chats</p>
          <div className="mobile-field">
            <label>Sarlavha</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Masalan: Haydovchi bilan suhbat"
              maxLength={255}
            />
          </div>
          <div className="mobile-field">
            <label>Kategoriya</label>
            <select value={category} onChange={(e) => setCategory(e.target.value as ChatCategory)}>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {CHAT_CATEGORY_LABELS[c] ?? c}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" className="mobile-btn mobile-btn-primary" disabled={creating}>
            {creating ? "..." : "Chat yaratish"}
          </button>
        </form>
      )}

      {loading && <p className="ai-chat-empty">Yuklanmoqda...</p>}

      <div className="ai-chats-list">
        {chats
          .filter((c) => c.category !== "ai_command")
          .map((chat) => (
            <Link key={chat.id} to={`/sender/chats/${chat.id}`} className="ai-chat-list-item">
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <strong>{chat.title || `#${chat.id}`}</strong>
                  <p className="ai-chat-list-meta">
                    {CHAT_CATEGORY_LABELS[chat.category] ?? chat.category} · {chat.status}
                  </p>
                </div>
                <ChevronRight size={18} color="var(--text-muted)" />
              </div>
            </Link>
          ))}
      </div>

      {!loading && chats.filter((c) => c.category !== "ai_command").length === 0 && (
        <p className="ai-chat-empty">Hali chat yo&apos;q. Yangi chat yarating.</p>
      )}
    </div>
  );
};
