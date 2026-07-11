import { apiRequest } from "../api";
import type {
  AssistantMessageResponse,
  AiUsageResponse,
  Chat,
  ChatListItem,
  ChatMessage,
  CreateChatPayload,
} from "../types/ai";



/**
 * GET /ai/assistant/chat — AI chat (asosiy endpoint)
 */
export async function fetchAssistantChat(): Promise<Chat> {
  return apiRequest<Chat>("/ai/assistant/chat");
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
