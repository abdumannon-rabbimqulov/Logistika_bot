/** ai/schemas.py — Chat & Message */

export type ChatCategory =
  | "complaint"
  | "suggestion"
  | "conversation"
  | "ai_command"
  | "support";

export type ChatStatus = "open" | "resolved" | "pending" | "escalated";

export type SenderType = "user" | "driver" | "ai" | "system";

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

/** POST /ai/chats — ChatBase */
export interface CreateChatPayload {
  category?: ChatCategory;
  status?: ChatStatus;
  title?: string | null;
  driver_id?: number | null;
  order_id?: number | null;
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
