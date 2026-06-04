import React, { createContext, useCallback, useContext, useState } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";

type ToastType = "success" | "error" | "info";

interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [items, setItems] = useState<ToastItem[]>([]);

  const toast = useCallback((message: string, type: ToastType = "info") => {
    const id = Date.now();
    setItems((prev) => [...prev, { id, type, message }]);
    setTimeout(() => setItems((prev) => prev.filter((t) => t.id !== id)), 4200);
  }, []);

  const dismiss = (id: number) => setItems((prev) => prev.filter((t) => t.id !== id));

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed top-4 right-4 z-[200] flex flex-col gap-2 max-w-sm w-full pointer-events-none px-4">
        {items.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 shadow-2xl backdrop-blur-md transition-all duration-300 ${
              t.type === "success"
                ? "border-emerald-500/30 bg-emerald-950/90 text-emerald-100"
                : t.type === "error"
                  ? "border-rose-500/30 bg-rose-950/90 text-rose-100"
                  : "border-cyan-500/30 bg-slate-900/95 text-slate-100"
            }`}
          >
            {t.type === "success" && <CheckCircle2 className="shrink-0 text-emerald-400" size={20} />}
            {t.type === "error" && <AlertCircle className="shrink-0 text-rose-400" size={20} />}
            {t.type === "info" && <Info className="shrink-0 text-cyan-400" size={20} />}
            <p className="text-sm flex-1 leading-snug">{t.message}</p>
            <button type="button" onClick={() => dismiss(t.id)} className="opacity-60 hover:opacity-100">
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
