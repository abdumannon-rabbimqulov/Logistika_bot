import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import styles from './Toast.module.css';

type ToastKind = 'success' | 'error';

interface ToastItem {
  id: number;
  kind: ToastKind;
  text: string;
}

interface ToastApi {
  success: (text: string) => void;
  error: (text: string) => void;
}

const ToastContext = createContext<ToastApi | null>(null);

const AUTO_HIDE_MS = 4000;

/** Admin panel uchun oddiy bildirishnoma (toast) — tashqi kutubxonasiz. */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const push = useCallback((kind: ToastKind, text: string) => {
    const id = Date.now() + Math.random();
    setItems((prev) => [...prev, { id, kind, text }]);
    window.setTimeout(() => setItems((prev) => prev.filter((t) => t.id !== id)), AUTO_HIDE_MS);
  }, []);

  const api = useMemo<ToastApi>(
    () => ({
      success: (text: string) => push('success', text),
      error: (text: string) => push('error', text),
    }),
    [push],
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className={styles.stack}>
        {items.map((t) => (
          <div key={t.id} className={t.kind === 'success' ? styles.success : styles.error} role="status">
            <span className={styles.icon}>{t.kind === 'success' ? '✓' : '!'}</span>
            <span>{t.text}</span>
            <button
              className={styles.close}
              aria-label="Yopish"
              onClick={() => setItems((prev) => prev.filter((x) => x.id !== t.id))}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/** Provider tashqarisida chaqirilsa xabar jim yo'qoladi — sahifa ishlashdan to'xtamaydi. */
export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  return ctx ?? { success: () => {}, error: () => {} };
}
