import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchChat, fetchChatMessages } from "../../services/aiApi";
import type { Chat, ChatMessage, MessageStatus, ReplyPreview } from "../../types/ai";
import { useAuth } from "../../context/AuthContext";
import { getWebSocketUrl } from "../../api";
import {
  Send,
  ArrowLeft,
  Check,
  CheckCheck,
  Clock,
  Reply,
  Pencil,
  Trash2,
  X,
  Paperclip,
  Image as ImageIcon,
  Mic,
} from "lucide-react";
import { VoiceRecorder } from "../../components/chat/VoiceRecorder";
import { VoicePlayer } from "../../components/chat/VoicePlayer";

// ─── Utility ───────────────────────────────────────────────────────────────────

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("uz-UZ", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function StatusIcon({ status, isMe }: { status?: MessageStatus; isMe: boolean }) {
  if (!isMe || !status) return null;
  const cls = "msg-status-icon";
  switch (status) {
    case "sending":   return <Clock size={12} className={`${cls} sending`} />;
    case "sent":      return <Check size={12} className={`${cls} sent`} />;
    case "delivered": return <CheckCheck size={12} className={`${cls} delivered`} />;
    case "read":      return <CheckCheck size={12} className={`${cls} read`} />;
    default:          return null;
  }
}

// ─── Typing indicator ─────────────────────────────────────────────────────────

const TypingIndicator: React.FC = () => (
  <div className="typing-indicator">
    <span /><span /><span />
    <p>yozmoqda...</p>
  </div>
);

// ─── ChatDetailPage ────────────────────────────────────────────────────────────

export const ChatDetailPage: React.FC = () => {
  const { chatId } = useParams<{ chatId: string }>();
  const navigate = useNavigate();
  const id = Number(chatId);
  const { user } = useAuth();

  const [chat, setChat]       = useState<Chat | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState("");
  const [input, setInput]       = useState("");

  // WS
  const [ws, setWs]                     = useState<WebSocket | null>(null);
  const [wsConnected, setWsConnected]   = useState(false);
  const [peerOnline, setPeerOnline]     = useState(false);
  const [peerLastSeen, setPeerLastSeen] = useState<string | null>(null);
  const [peerTyping, setPeerTyping]     = useState(false);

  // Telegram-like UX state
  const [replyTarget, setReplyTarget]   = useState<ReplyPreview | null>(null);
  const [editTarget, setEditTarget]     = useState<ChatMessage | null>(null);
  const [uploading, setUploading]       = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isRecordingVoice, setIsRecordingVoice] = useState(false);

  // Hold-to-record gesture state
  const [holdMode, setHoldMode]         = useState(false);
  const [slideOffset, setSlideOffset]   = useState(0);
  const holdTimerRef   = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pointerStartX  = useRef(0);
  const isHoldingRef   = useRef(false);

  const bottomRef   = useRef<HTMLDivElement>(null);
  const typingTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isTypingRef = useRef(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollDown = useCallback(() =>
    bottomRef.current?.scrollIntoView({ behavior: "smooth" }), []);

  // ── Initial load ────────────────────────────────────────────────
  useEffect(() => {
    if (!id || Number.isNaN(id)) return;
    setLoading(true);
    setError("");
    Promise.all([fetchChat(id), fetchChatMessages(id, { limit: 50 })])
      .then(([c, msgs]) => {
        setChat(c);
        setMessages(msgs.slice().sort((a, b) => a.id - b.id));
      })
      .catch((ex: unknown) => setError(ex instanceof Error ? ex.message : "Yuklanmadi"))
      .finally(() => setLoading(false));
  }, [id]);

  // ── WebSocket ────────────────────────────────────────────────────
  useEffect(() => {
    if (!id || Number.isNaN(id) || loading || !chat) return;
    const token = localStorage.getItem("logistika_access_token");
    if (!token) return;

    const socket = new WebSocket(getWebSocketUrl(`/ai/ws/${id}?token=${token}`));

    socket.onopen = () => setWsConnected(true);
    socket.onclose = () => setWsConnected(false);

    socket.onmessage = (evt) => {
      try {
        const payload = JSON.parse(evt.data as string);

        switch (payload.event) {
          case "connected": {
            const { messages: hist, online_peers, peer_last_seen } = payload.data ?? {};
            if (hist?.length) {
              setMessages((prev) => {
                const map = new Map(prev.map((m) => [m.id, m]));
                (hist as ChatMessage[]).forEach((m) => map.set(m.id, m));
                return Array.from(map.values()).sort((a, b) => a.id - b.id);
              });
            }
            if (online_peers?.length) setPeerOnline(true);
            if (peer_last_seen) setPeerLastSeen(peer_last_seen);
            break;
          }

          case "new_message": {
            const msg = payload.data as ChatMessage;
            setMessages((prev) => {
              if (prev.some((m) => m.id === msg.id)) return prev;
              return [...prev, msg];
            });
            // Mark as read if chat is open, EXCEPT for voice messages
            const isVoice = msg.message_type === "voice" || msg.attachments?.some(a => a.file_type === "voice");
            if (msg.sender_id !== user?.id && !isVoice) {
              socket.send(JSON.stringify({ type: "message_read", message_ids: [msg.id] }));
              // Emit to global bus for ChatsPage badge
              window.dispatchEvent(new CustomEvent("ws:new_message", { detail: { chat_id: id } }));
            }
            break;
          }

          case "delivery_update": {
            const { message_id, message_ids, status } = payload.data as {
              message_id?: number;
              message_ids?: number[];
              status: MessageStatus;
            };
            const ids = message_ids ?? (message_id ? [message_id] : []);
            setMessages((prev) =>
              prev.map((m) => (ids.includes(m.id) ? { ...m, status } : m))
            );
            break;
          }

          case "typing": {
            const { user_id, is_typing } = payload.data as { user_id: number; is_typing: boolean };
            if (user_id !== user?.id) {
              setPeerTyping(is_typing);
              if (is_typing) {
                setTimeout(() => setPeerTyping(false), 3500);
              }
            }
            break;
          }

          case "user_presence": {
            const { user_id, online, last_seen } = payload.data as {
              user_id: number; online: boolean; last_seen?: string;
            };
            if (user_id !== user?.id) {
              setPeerOnline(online);
              if (!online && last_seen) setPeerLastSeen(last_seen);
              window.dispatchEvent(
                new CustomEvent("ws:user_presence", { detail: { chat_id: id, online, last_seen } })
              );
            }
            break;
          }

          case "message_edited": {
            const updated = payload.data as ChatMessage;
            setMessages((prev) => prev.map((m) => (m.id === updated.id ? updated : m)));
            break;
          }

          case "message_deleted": {
            const { message_id } = payload.data as { message_id: number };
            setMessages((prev) =>
              prev.map((m) =>
                m.id === message_id
                  ? { ...m, is_deleted: true, content: null }
                  : m
              )
            );
            break;
          }

          default:
            break;
        }
      } catch (err) {
        console.error("WS parse error:", err);
      }
    };

    setWs(socket);
    return () => socket.close();
  }, [id, loading, chat, user?.id]);

  // ── Scroll on new messages ──────────────────────────────────────
  useEffect(() => { scrollDown(); }, [messages, scrollDown]);

  // ── Typing broadcast (debounced) ────────────────────────────────
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    if (!isTypingRef.current) {
      isTypingRef.current = true;
      ws.send(JSON.stringify({ type: "typing_start" }));
    }
    if (typingTimer.current) clearTimeout(typingTimer.current);
    typingTimer.current = setTimeout(() => {
      isTypingRef.current = false;
      ws?.send(JSON.stringify({ type: "typing_stop" }));
    }, 2500);
  };

  // ── Send / Edit submit ──────────────────────────────────────────
  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;

    // Stop typing signal
    if (isTypingRef.current) {
      isTypingRef.current = false;
      if (typingTimer.current) clearTimeout(typingTimer.current);
      ws.send(JSON.stringify({ type: "typing_stop" }));
    }

    if (editTarget) {
      // Edit mode
      ws.send(JSON.stringify({ type: "message_edit", message_id: editTarget.id, content: text }));
      setEditTarget(null);
    } else {
      // New message
      const payload: Record<string, unknown> = {
        type: "new_message",
        content: text,
        uuid: crypto.randomUUID(),
      };
      if (replyTarget) payload.reply_to_id = replyTarget.id;
      ws.send(JSON.stringify(payload));
      setReplyTarget(null);
    }
    setInput("");
  };

  // ── Context menu actions ────────────────────────────────────────
  const startReply = (msg: ChatMessage) => {
    setEditTarget(null);
    setReplyTarget({
      id: msg.id,
      content: msg.content,
      sender_type: msg.sender_type,
      message_type: msg.message_type,
    });
    document.getElementById("chat-input")?.focus();
  };

  const startEdit = (msg: ChatMessage) => {
    setReplyTarget(null);
    setEditTarget(msg);
    setInput(msg.content ?? "");
    document.getElementById("chat-input")?.focus();
  };

  const deleteMsg = (msg: ChatMessage) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: "message_delete", message_id: msg.id }));
  };

  // ── File upload ─────────────────────────────────────────────────
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";

    const token = localStorage.getItem("logistika_access_token");
    if (!token) return;

    const form = new FormData();
    form.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.upload.addEventListener("progress", (ev) => {
      if (ev.lengthComputable) setUploadProgress(Math.round((ev.loaded / ev.total) * 100));
    });
    xhr.addEventListener("load", () => { setUploading(false); setUploadProgress(0); });
    xhr.addEventListener("error", () => { setUploading(false); setUploadProgress(0); });

    xhr.open("POST", `/api/ai/chats/${id}/upload`);
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    setUploading(true);
    xhr.send(form);
  };

  const handleVoiceSend = (file: File) => {
    setIsRecordingVoice(false);
    const token = localStorage.getItem("logistika_access_token");
    if (!token) return;

    const form = new FormData();
    form.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.upload.addEventListener("progress", (ev) => {
      if (ev.lengthComputable) setUploadProgress(Math.round((ev.loaded / ev.total) * 100));
    });
    xhr.addEventListener("load", () => { setUploading(false); setUploadProgress(0); });
    xhr.addEventListener("error", () => { setUploading(false); setUploadProgress(0); });

    xhr.open("POST", `/api/ai/chats/${id}/upload`);
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    setUploading(true);
    xhr.send(form);
  };

  const markVoiceAsRead = (msgId: number) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: "message_read", message_ids: [msgId] }));
  };

  // ── Hold-to-record gesture handlers ────────────────────────────

  const HOLD_DELAY = 500; // ms before hold-mode activates

  const handleMicPointerDown = (e: React.PointerEvent) => {
    e.preventDefault();
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
    pointerStartX.current = e.clientX;
    isHoldingRef.current = true;
    setSlideOffset(0);

    // Start a timer — if held for HOLD_DELAY, enter hold-mode
    holdTimerRef.current = setTimeout(() => {
      if (isHoldingRef.current) {
        setHoldMode(true);
        setIsRecordingVoice(true);
      }
    }, HOLD_DELAY);
  };

  const handleMicPointerMove = (e: React.PointerEvent) => {
    if (!isHoldingRef.current || !holdMode) return;
    const dx = e.clientX - pointerStartX.current;
    setSlideOffset(Math.min(0, dx)); // only allow leftward drag
  };

  const handleMicPointerUp = async () => {
    isHoldingRef.current = false;
    if (holdTimerRef.current) {
      clearTimeout(holdTimerRef.current);
      holdTimerRef.current = null;
    }

    if (holdMode && isRecordingVoice) {
      // Hold-mode release — VoiceRecorder's parent tells it to stop+send
      // We dispatch a custom event that VoiceRecorder listens to
      window.dispatchEvent(new CustomEvent("voice:hold-release"));
      setHoldMode(false);
      setSlideOffset(0);
    } else if (!isRecordingVoice) {
      // Short tap — toggle into tap-mode recording
      setHoldMode(false);
      setIsRecordingVoice(true);
    }
  };

  // ─────────────────────────────────────────────────────────────────

  const presenceLabel = peerOnline
    ? "Online"
    : peerLastSeen
    ? `Oxirgi: ${new Date(peerLastSeen).toLocaleTimeString("uz-UZ", { hour: "2-digit", minute: "2-digit" })}`
    : "";

  if (loading) return <p className="ai-chat-empty">Chat yuklanmoqda...</p>;
  if (error) return <div className="mobile-alert mobile-alert-error">{error}</div>;
  if (!chat) return <p className="ai-chat-empty">Chat topilmadi</p>;

  return (
    <div className="tg-chat-page">
      {/* ── Header ── */}
      <div className="tg-chat-header">
        <button className="tg-back-btn" onClick={() => navigate(-1)} aria-label="Orqaga">
          <ArrowLeft size={20} />
        </button>
        <div className="tg-chat-avatar">
          {(chat.title ?? `#${chat.id}`)[0]?.toUpperCase()}
        </div>
        <div className="tg-chat-header-info">
          <p className="tg-chat-header-title">{chat.title ?? `Chat #${chat.id}`}</p>
          <p className={`tg-chat-header-sub ${peerOnline ? "online" : "offline"}`}>
            {peerOnline ? "🟢 Online" : presenceLabel || (wsConnected ? "Ulandi" : "Ulanmoqda...")}
          </p>
        </div>
      </div>

      {/* ── Messages ── */}
      <div className="tg-messages-area">
        {messages.length === 0 && !loading && (
          <p className="ai-chat-empty">Suhbatni boshlash uchun birinchi xabarni yozing.</p>
        )}

        {messages.map((m) => {
          const isMe = m.sender_id === user?.id;
          const isSystem = m.sender_type === "system";

          if (isSystem) {
            return (
              <div key={m.id} className="tg-system-msg">
                <span>{m.content}</span>
              </div>
            );
          }

          return (
            <div key={m.id} className={`tg-bubble-wrap ${isMe ? "me" : "them"}`}>
              <div className={`tg-bubble ${isMe ? "bubble-me" : "bubble-them"}`}>
                {/* Reply quote */}
                {m.reply_to && (
                  <div className="tg-reply-quote">
                    <div className="tg-reply-bar" />
                    <div>
                      <p className="tg-reply-sender">
                        {m.reply_to.sender_type === "driver" ? "Haydovchi" : "Mijoz"}
                      </p>
                      <p className="tg-reply-text">{m.reply_to.content ?? "📎 Media"}</p>
                    </div>
                  </div>
                )}

                {/* Attachments */}
                {m.attachments?.length > 0 && (
                  <div className="tg-attachments">
                    {m.attachments.map((att) => {
                      if (att.file_type === "image") {
                        return <img key={att.id} src={att.file_url} alt={att.original_name ?? "rasm"} className="tg-img" />;
                      }
                      if (att.file_type === "voice") {
                        return (
                          <VoicePlayer 
                            key={att.id} 
                            src={att.file_url} 
                            onFinishedListening={() => {
                              if (!isMe && m.status !== "read") {
                                markVoiceAsRead(m.id);
                              }
                            }} 
                          />
                        );
                      }
                      return (
                        <a key={att.id} href={att.file_url} target="_blank" rel="noreferrer" className="tg-file-link">
                          <Paperclip size={14} />
                          {att.original_name ?? "Fayl"}
                        </a>
                      );
                    })}
                  </div>
                )}

                {/* Content */}
                {m.is_deleted ? (
                  <em className="tg-deleted">Xabar o'chirildi</em>
                ) : (
                  <p className="tg-bubble-text">{m.content}</p>
                )}

                {/* Footer: time + ticks */}
                <div className="tg-bubble-footer">
                  {m.edited_at && !m.is_deleted && (
                    <span className="tg-edited">tahrirlandi</span>
                  )}
                  <time className="tg-bubble-time">{formatTime(m.created_at)}</time>
                  <StatusIcon status={m.status} isMe={isMe} />
                </div>

                {/* Actions (hover) */}
                {!m.is_deleted && (
                  <div className="tg-bubble-actions">
                    <button
                      className="tg-action-btn"
                      onClick={() => startReply(m)}
                      title="Javob berish"
                    >
                      <Reply size={14} />
                    </button>
                    {isMe && (
                      <>
                        <button
                          className="tg-action-btn"
                          onClick={() => startEdit(m)}
                          title="Tahrirlash"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          className="tg-action-btn danger"
                          onClick={() => deleteMsg(m)}
                          title="O'chirish"
                        >
                          <Trash2 size={14} />
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Typing indicator */}
        {peerTyping && (
          <div className="tg-bubble-wrap them">
            <div className="tg-bubble bubble-them">
              <TypingIndicator />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Upload progress ── */}
      {uploading && (
        <div className="tg-upload-progress">
          <div className="tg-upload-bar" style={{ width: `${uploadProgress}%` }} />
          <span>{uploadProgress}% yuklanyapti...</span>
        </div>
      )}

      {/* ── Reply / Edit bar ── */}
      {(replyTarget || editTarget) && (
        <div className="tg-context-bar">
          <div className="tg-context-bar-indicator" />
          <div className="tg-context-bar-content">
            <p className="tg-context-bar-label">
              {editTarget ? "Tahrirlash" : "Javob berish"}
            </p>
            <p className="tg-context-bar-preview">
              {(editTarget?.content ?? replyTarget?.content) ?? "📎 Media"}
            </p>
          </div>
          <button
            className="tg-context-bar-close"
            onClick={() => { setReplyTarget(null); setEditTarget(null); setInput(""); }}
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* ── Input bar ── */}
      <form className="tg-input-bar" onSubmit={handleSend}>
        {isRecordingVoice ? (
          <VoiceRecorder 
            chatId={id} 
            onSend={handleVoiceSend} 
            onCancel={() => { setIsRecordingVoice(false); setHoldMode(false); setSlideOffset(0); }} 
            holdMode={holdMode}
            slideOffset={slideOffset}
          />
        ) : (
          <>
            {/* File attach */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*,video/*,application/pdf,.doc,.docx"
              style={{ display: "none" }}
              onChange={handleFileChange}
            />
            <button
              type="button"
              className="tg-attach-btn"
              onClick={() => fileInputRef.current?.click()}
              aria-label="Fayl biriktirish"
              disabled={uploading}
            >
              <Paperclip size={20} />
            </button>

            <textarea
              id="chat-input"
              rows={1}
              placeholder="Xabarni yozing..."
              value={input}
              onChange={handleInputChange}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend(e as unknown as React.FormEvent);
                }
              }}
              disabled={!wsConnected}
              className="tg-textarea"
            />

            {input.trim() ? (
              <button
                type="submit"
                className="tg-send-btn"
                disabled={!wsConnected}
                aria-label="Yuborish"
              >
                <Send size={20} />
              </button>
            ) : (
              <button
                type="button"
                className={`tg-send-btn mic-btn${isHoldingRef.current ? ' mic-holding' : ''}`}
                disabled={!wsConnected}
                onPointerDown={handleMicPointerDown}
                onPointerMove={handleMicPointerMove}
                onPointerUp={handleMicPointerUp}
                onPointerCancel={() => {
                  isHoldingRef.current = false;
                  if (holdTimerRef.current) clearTimeout(holdTimerRef.current);
                }}
                aria-label="Ovoz yozish"
              >
                <Mic size={20} />
              </button>
            )}
          </>
        )}
      </form>
    </div>
  );
};
