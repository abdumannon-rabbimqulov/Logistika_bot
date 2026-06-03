/** Telegram Mini App — kelajakda init_data avtomatik login uchun. */

export interface TelegramWebApp {
  initData: string;
  ready: () => void;
  expand?: () => void;
  close?: () => void;
}

declare global {
  interface Window {
    Telegram?: {
      WebApp?: TelegramWebApp;
    };
  }
}

export function getTelegramInitData(): string | undefined {
  const initData = window.Telegram?.WebApp?.initData?.trim();
  return initData || undefined;
}

export function isTelegramWebApp(): boolean {
  return Boolean(getTelegramInitData());
}

export function initTelegramWebApp(): void {
  const tg = window.Telegram?.WebApp;
  if (!tg) return;
  tg.ready();
  tg.expand?.();
}
