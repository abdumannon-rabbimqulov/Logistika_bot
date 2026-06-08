import React, { useState, useEffect } from "react";
import { X, Send } from "lucide-react";

interface OfferModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (price: number, comment: string) => Promise<void>;
  orderPrice: string | number;
  orderCurrency: string;
  busy: boolean;
}

export const OfferModal: React.FC<OfferModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  orderPrice,
  orderCurrency,
  busy,
}) => {
  const [price, setPrice] = useState<string>("");
  const [comment, setComment] = useState<string>("");

  useEffect(() => {
    if (isOpen) {
      setPrice(String(orderPrice));
      setComment("");
    }
  }, [isOpen, orderPrice]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const p = Number(price);
    if (!p || p <= 0) return;
    await onSubmit(p, comment);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm transition-opacity">
      <div className="w-full max-w-sm rounded-2xl bg-slate-900 border border-slate-700 shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between p-4 border-b border-slate-800">
          <h3 className="font-semibold text-white">Taklif kiritish</h3>
          <button
            onClick={onClose}
            disabled={busy}
            className="text-slate-400 hover:text-white transition disabled:opacity-50"
          >
            <X size={20} />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Sizning narxingiz ({orderCurrency})
            </label>
            <input
              type="number"
              value={price}
              onChange={(e) => setPrice(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 transition"
              required
              min="0"
              disabled={busy}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">
              Izoh yoki shartlar
            </label>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Masalan: Ertalab soat 10:00 da boraman..."
              className="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 transition min-h-[80px]"
              disabled={busy}
            />
          </div>
          <button
            type="submit"
            disabled={busy || !price || Number(price) <= 0}
            className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 py-2.5 text-sm font-semibold text-white disabled:opacity-50 active:scale-[0.99] transition mt-2"
          >
            <Send size={16} />
            {busy ? "Yuborilmoqda..." : "Taklifni jo'natish"}
          </button>
        </form>
      </div>
    </div>
  );
};
