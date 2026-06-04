import { apiRequest } from "../api";
import type {
  AssistantMessageResponse,
  AiUsageResponse,
  Chat,
  ChatMessage,
  CreateChatPayload,
} from "../types/ai";

/** POST /ai/chats — yangi chat */
export async function createChat(data: CreateChatPayload = {}): Promise<Chat> {
  return apiRequest<Chat>("/ai/chats", {
    method: "POST",
    body: JSON.stringify({
      category: data.category ?? "conversation",
      status: data.status ?? "open",
      title: data.title ?? null,
      driver_id: data.driver_id ?? null,
      order_id: data.order_id ?? null,
    }),
  });
}

/** GET /ai/chats — mening chatlarim */
export async function fetchMyChats(): Promise<Chat[]> {
  return apiRequest<Chat[]>("/ai/chats");
}

/** GET /ai/chats/{chat_id} — chat tafsilotlari */
export async function fetchChat(chatId: number): Promise<Chat> {
  return apiRequest<Chat>(`/ai/chats/${chatId}`);
}

/**
 * GET /ai/assistant/chat — AI chat (asosiy endpoint)
 */
export async function fetchAssistantChat(): Promise<Chat> {
  return apiRequest<Chat>("/ai/assistant/chat");
}

/** GET /ai/chats/{chat_id}/messages */
export async function fetchChatMessages(
  chatId: number,
  params?: { limit?: number; before_id?: number }
): Promise<ChatMessage[]> {
  const q = new URLSearchParams();
  if (params?.limit) q.set("limit", String(params.limit));
  if (params?.before_id) q.set("before_id", String(params.before_id));
  const qs = q.toString();
  return apiRequest<ChatMessage[]>(`/ai/chats/${chatId}/messages${qs ? `?${qs}` : ""}`);
}

/** GET /ai/assistant/messages */
export async function fetchAssistantMessages(params?: {
  chat_id?: number;
  limit?: number;
  before_id?: number;
}): Promise<ChatMessage[]> {
  const q = new URLSearchParams();
  if (params?.chat_id) q.set("chat_id", String(params.chat_id));
  if (params?.limit) q.set("limit", String(params.limit));
  if (params?.before_id) q.set("before_id", String(params.before_id));
  const qs = q.toString();
  return apiRequest<ChatMessage[]>(`/ai/assistant/messages${qs ? `?${qs}` : ""}`);
}

/** POST /ai/assistant/message */
export async function sendAssistantMessage(
  message: string,
  chatId?: number
): Promise<AssistantMessageResponse> {
  return apiRequest<AssistantMessageResponse>("/ai/assistant/message", {
    method: "POST",
    body: JSON.stringify({ message, chat_id: chatId ?? null }),
  });
}

/** GET /ai/me/usage */
export async function fetchMyAiUsage(): Promise<AiUsageResponse> {
  return apiRequest<AiUsageResponse>("/ai/me/usage");
}

export const CHAT_CATEGORY_LABELS: Record<string, string> = {
  conversation: "Suhbat",
  complaint: "Shikoyat",
  suggestion: "Taklif",
  ai_command: "AI yordamchi",
  support: "Qo'llab-quvvatlash",
};
