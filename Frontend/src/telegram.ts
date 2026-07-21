// Telegram WebApp SDK — npm paket sifatida emas, index.html'dagi rasmiy
// <script src="https://telegram.org/js/telegram-web-app.js"> orqali yuklanadi.
// Bu yerda faqat biz ishlatadigan qismning yengil TS turi e'lon qilingan.

interface TelegramWebAppUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
  language_code?: string;
}

interface TelegramHapticFeedback {
  impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void;
  notificationOccurred: (type: 'error' | 'success' | 'warning') => void;
  selectionChanged: () => void;
}

interface TelegramMainButton {
  text: string;
  isVisible: boolean;
  show: () => void;
  hide: () => void;
  setText: (text: string) => void;
  onClick: (cb: () => void) => void;
  offClick: (cb: () => void) => void;
  enable: () => void;
  disable: () => void;
}

interface TelegramBackButton {
  isVisible: boolean;
  show: () => void;
  hide: () => void;
  onClick: (cb: () => void) => void;
  offClick: (cb: () => void) => void;
}

interface TelegramWebApp {
  initData: string;
  initDataUnsafe: { user?: TelegramWebAppUser };
  platform: string;
  colorScheme: 'light' | 'dark';
  ready: () => void;
  expand: () => void;
  close: () => void;
  MainButton: TelegramMainButton;
  BackButton: TelegramBackButton;
  HapticFeedback: TelegramHapticFeedback;
}

declare global {
  interface Window {
    Telegram?: { WebApp: TelegramWebApp };
  }
}

export function getTelegramWebApp(): TelegramWebApp | null {
  return window.Telegram?.WebApp ?? null;
}

/** Bot orqali ochilmagan (oddiy brauzerda dev/test) holatda ham ilova ishlashi uchun. */
export function getInitData(): string {
  return getTelegramWebApp()?.initData ?? '';
}

export function initTelegramWebApp(): void {
  const webApp = getTelegramWebApp();
  if (!webApp) return;
  webApp.ready();
  webApp.expand();
}

export function haptic(style: 'light' | 'medium' | 'heavy' = 'light'): void {
  getTelegramWebApp()?.HapticFeedback.impactOccurred(style);
}

/** Register formasini oldindan to'ldirish uchun — faqat taxminiy, auth uchun ishlatilmaydi. */
export function getTelegramUser(): TelegramWebAppUser | null {
  return getTelegramWebApp()?.initDataUnsafe.user ?? null;
}
