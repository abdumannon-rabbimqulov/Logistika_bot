import React from "react";
import type { OrderStatus } from "../../types/order";

const STATUS_META: Record<
  OrderStatus,
  { label: string; className: string }
> = {
  PENDING: { label: "Kutilmoqda", className: "bg-amber-500/15 text-amber-300 ring-amber-500/30" },
  ACCEPTED: { label: "Qabul qilindi", className: "bg-sky-500/15 text-sky-300 ring-sky-500/30" },
  IN_PROGRESS: { label: "Jarayonda", className: "bg-cyan-500/15 text-cyan-300 ring-cyan-500/30" },
  COMPLETED: { label: "Yakunlangan", className: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30" },
  CANCELLED: { label: "Bekor qilindi", className: "bg-rose-500/15 text-rose-300 ring-rose-500/30" },
};

export const OrderStatusBadge: React.FC<{ status: OrderStatus | string }> = ({ status }) => {
  const key = (status?.toUpperCase?.() ?? status) as OrderStatus;
  const meta = STATUS_META[key] ?? {
    label: String(status),
    className: "bg-slate-500/15 text-slate-300 ring-slate-500/30",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[11px] font-semibold ring-1 ${meta.className}`}
    >
      {meta.label}
    </span>
  );
};
