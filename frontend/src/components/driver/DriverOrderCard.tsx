import React from "react";
import { Link } from "react-router-dom";
import {
  Check,
  Flag,
  MapPin,
  Package,
  Scale,
  Send,
  Tag,
  Truck,
} from "lucide-react";
import type { Order, OrderWaypoint } from "../../types/order";

function cityFromAddress(address: string): string {
  const part = address.split(",")[0]?.trim() || address.trim();
  return part.length > 28 ? `${part.slice(0, 26)}…` : part;
}

function waypointAction(
  wp: OrderWaypoint,
  index: number,
  total: number
): { label: string; Icon: typeof MapPin; iconClass: string; badgeClass: string } {
  const t = wp.waypoint_type.toLowerCase();
  if (t === "pickup" || index === 0) {
    return {
      label: "Yuklash",
      Icon: MapPin,
      iconClass: "text-emerald-400",
      badgeClass: "bg-emerald-500/20 ring-emerald-500/40",
    };
  }
  if (t === "delivery" && index === total - 1) {
    return {
      label: "Yetkazish",
      Icon: Flag,
      iconClass: "text-rose-400",
      badgeClass: "bg-rose-500/20 ring-rose-500/40",
    };
  }
  if (t === "delivery") {
    return {
      label: "Yuk tushirish",
      Icon: Package,
      iconClass: "text-sky-400",
      badgeClass: "bg-sky-500/20 ring-sky-500/40",
    };
  }
  return {
    label: "Oraliq",
    Icon: Package,
    iconClass: "text-violet-400",
    badgeClass: "bg-violet-500/20 ring-violet-500/40",
  };
}

const STATUS_STYLES: Record<string, string> = {
  PENDING: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  ACCEPTED: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30",
  IN_PROGRESS: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  COMPLETED: "bg-slate-500/15 text-slate-300 border-slate-500/30",
  CANCELLED: "bg-rose-500/15 text-rose-300 border-rose-500/30",
};

interface DriverOrderCardProps {
  order: Order;
  busy?: boolean;
  showOfferButton?: boolean;
  onOffer?: (order: Order) => void;
  onAccept?: (order: Order) => void;
  truckTypeName?: string;
}

export const DriverOrderCard: React.FC<DriverOrderCardProps> = ({
  order,
  busy,
  showOfferButton = true,
  onOffer,
  onAccept,
  truckTypeName,
}) => {
  const sorted = [...(order.waypoints ?? [])].sort((a, b) => a.sequence - b.sequence);
  const initial = String.fromCharCode(65 + (order.customer_id % 26));
  const statusClass =
    STATUS_STYLES[order.status] ?? STATUS_STYLES.PENDING;

  return (
    <article className="rounded-2xl border border-white/8 bg-slate-800/50 backdrop-blur-md overflow-hidden shadow-lg shadow-black/25 hover:border-cyan-500/30 transition-all">
      <Link to={`/driver/orders/${order.id}`} className="block no-underline text-inherit hover:text-inherit">
        <div className="flex items-center justify-between gap-2 px-4 pt-4 pb-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-cyan-500/30 to-violet-600/30 text-sm font-bold text-white ring-1 ring-white/15">
              {initial}
            </span>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-white truncate">{order.cargo_name}</p>
              <p className="text-[11px] text-slate-500 truncate">Buyurtma #{order.id}</p>
            </div>
          </div>
          <span
            className={`shrink-0 rounded-lg border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide ${statusClass}`}
          >
            {order.status}
          </span>
        </div>

        <div className="mx-4 mb-3 rounded-xl bg-slate-900/60 border border-white/5 px-3 py-3">
          <div className="relative space-y-0">
            {sorted.map((wp, index) => {
              const { label, Icon, iconClass, badgeClass } = waypointAction(
                wp,
                index,
                sorted.length
              );
              const isLast = index === sorted.length - 1;

              return (
                <div key={wp.id} className="flex gap-3 relative">
                  {!isLast && (
                    <span
                      className="absolute left-[15px] top-8 bottom-0 w-0 border-l-2 border-dashed border-slate-600/80"
                      aria-hidden
                    />
                  )}
                  <span
                    className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ring-1 ${badgeClass}`}
                  >
                    <Icon size={16} className={iconClass} />
                  </span>
                  <div className={`flex-1 min-w-0 ${isLast ? "pb-0" : "pb-4"}`}>
                    <p className="text-[10px] font-bold text-slate-500">
                      {index + 1}. {cityFromAddress(wp.address)}
                    </p>
                    <p className="text-xs font-medium text-slate-200 mt-0.5">{label}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5 line-clamp-1">
                      {wp.address}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="px-4 pb-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-400">
          <span className="inline-flex items-center gap-1.5">
            <Scale size={14} className="text-amber-400/90" />
            {order.weight} Tonna
          </span>
          <span className="inline-flex items-center gap-1.5">
            <Truck size={14} className="text-cyan-400/90" />
            {truckTypeName || "Yuk mashinasi"}
          </span>
          <span className="inline-flex items-center gap-1.5 ml-auto">
            <Tag size={14} className="text-emerald-400/90" />
            <span className="text-sm font-bold text-white">
              {Number(order.price).toLocaleString()} {order.currency}
            </span>
          </span>
        </div>
      </Link>

      {showOfferButton && onOffer && (
        <div className="px-4 pb-4 grid grid-cols-2 gap-3">
          <button
            type="button"
            disabled={busy}
            onClick={() => onAccept?.(order)}
            className="w-full flex items-center justify-center gap-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 py-2.5 text-xs font-bold text-white disabled:opacity-50 active:scale-[0.99] transition"
          >
            <Check size={14} />
            Qabul qilish
          </button>

          <button
            type="button"
            disabled={busy}
            onClick={() => onOffer(order)}
            className="w-full flex items-center justify-center gap-1.5 rounded-xl bg-slate-800/85 hover:bg-slate-700 border border-white/10 py-2.5 text-xs font-semibold text-slate-300 disabled:opacity-50 active:scale-[0.99] transition"
          >
            <Send size={14} />
            Taklif berish
          </button>
        </div>
      )}
    </article>
  );
};
