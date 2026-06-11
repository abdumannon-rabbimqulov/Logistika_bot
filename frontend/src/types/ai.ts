/** ai/schemas.py — Chat & Message (Telegram-like extended) */

export type ChatCategory =
  | "complaint"
  | "suggestion"
  | "conversation"
  | "ai_command"
  | "support";

export type ChatStatus = "open" | "resolved" | "pending" | "escalated";

export type SenderType = "user" | "driver" | "ai" | "system";

/** Delivery status — matches MessageStatus enum in backend */
export type MessageStatus = "sending" | "sent" | "delivered" | "read";

export interface Chat {
  id: number;
  category: ChatCategory;
  status: ChatStatus;
  title?: string | null;
  user_id?: number | null;
  driver_id?: number | null;
  order_id?: number | null;
  created_at: string;
  updated_at?: string | null;
  closed_at?: string | null;
}

/** GET /ai/chats — ChatListItem (with presence + unread) */
export interface ChatListItem {
  id: number;
  title?: string | null;
  order_id?: number | null;
  category: ChatCategory;
  last_message?: ChatMessage | null;
  unread_count: number;
  peer_online: boolean;
  peer_last_seen?: string | null;
  updated_at?: string | null;
}

/** POST /ai/chats — ChatBase */
export interface CreateChatPayload {
  category?: ChatCategory;
  status?: ChatStatus;
  title?: string | null;
  driver_id?: number | null;
  order_id?: number | null;
}

/** Nested reply preview inside a message */
export interface ReplyPreview {
  id: number;
  content?: string | null;
  sender_type: SenderType;
  message_type: string;
}

export interface ChatAttachment {
  id: number;
  message_id: number;
  file_type: "image" | "video" | "voice" | "file";
  file_url: string;
  original_name?: string | null;
  mime_type?: string | null;
  file_size?: number | null;
  created_at: string;
}

export interface ChatMessage {
  id: number;
  chat_id: number;
  sender_id?: number | null;
  sender_type: SenderType;
  message_type: string;
  content?: string | null;
  is_read: boolean;
  is_ai_response: boolean;
  is_ai_command: boolean;
  /** Delivery status (Telegram-like ticks) */
  status: MessageStatus;
  is_deleted: boolean;
  reply_to?: ReplyPreview | null;
  client_uuid?: string | null;
  attachments: ChatAttachment[];
  created_at: string;
  edited_at?: string | null;
}

export interface AssistantMessageResponse {
  reply: string;
  chat_id: number;
  used_today: number;
  daily_limit: number;
  allowed: boolean;
}

export interface AiUsageResponse {
  allowed: boolean;
  used_today: number;
  daily_limit: number;
}
