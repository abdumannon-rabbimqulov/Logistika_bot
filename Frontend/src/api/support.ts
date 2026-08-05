// Support mikroservisi bilan ishlash (murojaatlar / ticketlar).
//
// Bu xizmat asosiy backenddan ALOHIDA: o'z konteyneri, o'z bazasi (`support_db`) va o'z
// prefiksi (`/support`, `/api` ostida emas). Shuning uchun `api` emas, `supportApi`
// wrapper'i ishlatiladi — u faqat bazasi bilan farq qiladi, token va 401→refresh mantiqi
// bir xil (support ham xuddi shu access tokenni umumiy SECRET_KEY bilan tekshiradi).

import { supportApi } from './client';
import type {
  TicketCreateInput,
  TicketDetail,
  TicketListItem,
  TicketMessage,
  TicketStatus,
} from '../types/api';

export interface ListTicketsParams {
  status?: TicketStatus;
  order_id?: number;
  /** Xodim uchun: hammasi emas, faqat o'z murojaatlarini ko'rsatish.
   *  Oddiy foydalanuvchida ta'siri yo'q — u baribir faqat o'zinikini ko'radi. */
  mine?: boolean;
  limit?: number;
  offset?: number;
}

export function listTickets(params: ListTicketsParams = {}): Promise<TicketListItem[]> {
  return supportApi.get<TicketListItem[]>('/support/tickets', {
    status: params.status,
    order_id: params.order_id,
    mine: params.mine,
    limit: params.limit,
    offset: params.offset,
  });
}

export function getTicket(ticketId: number): Promise<TicketDetail> {
  return supportApi.get<TicketDetail>(`/support/tickets/${ticketId}`);
}

export function createTicket(data: TicketCreateInput): Promise<TicketDetail> {
  return supportApi.post<TicketDetail>('/support/tickets', data);
}

/** Yopilgan murojaatga javob yozib bo'lmaydi — backend 409 qaytaradi.
 *  Javob sifatida butun ticket emas, faqat yangi yozilgan xabar qaytadi. */
export function replyToTicket(ticketId: number, body: string): Promise<TicketMessage> {
  return supportApi.post<TicketMessage>(`/support/tickets/${ticketId}/messages`, { body });
}

/** Faqat xodim (admin/manager) uchun — `require_staff`. */
export function updateTicketStatus(
  ticketId: number,
  status: TicketStatus,
): Promise<TicketDetail> {
  return supportApi.patch<TicketDetail>(`/support/tickets/${ticketId}/status`, { status });
}

/** Holat nomlarining o'zbekcha ko'rinishi — ro'yxat va tafsilot ekranlarida bir xil. */
export const TICKET_STATUS_LABELS: Record<TicketStatus, string> = {
  open: 'Ochiq',
  in_progress: 'Ko’rib chiqilmoqda',
  resolved: 'Hal qilindi',
  closed: 'Yopilgan',
};

export const TICKET_PRIORITY_LABELS: Record<string, string> = {
  low: 'Past',
  normal: 'Oddiy',
  high: 'Yuqori',
  urgent: 'Shoshilinch',
};

/** Yopilgan/hal qilingan murojaatga yangi xabar yozilmaydi (support_service/models.py). */
export function isTicketClosed(status: TicketStatus): boolean {
  return status === 'closed' || status === 'resolved';
}
