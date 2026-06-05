import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ChevronRight, Loader2, Package, Plus, RefreshCw } from "lucide-react";
import { fetchSenderOrders } from "../../services/senderApi";
import { OrderStatusBadge } from "../../components/sender/OrderStatusBadge";
import { Skeleton } from "../../components/ui/Skeleton";
import { useToast } from "../../components/ui/Toast";
import type { Order, OrderStatus, SenderOrderTab } from "../../types/order";
import { SENDER_ACTIVE_STATUSES } from "../../types/order";

const TABS: { key: SenderOrderTab; label: string }[] = [
  { key: "PENDING", label: "Kutilmoqda" },
  { key: "ACTIVE", label: "Faol" },
  { key: "COMPLETED", label: "Yakunlangan" },
];

function filterByTab(orders: Order[], tab: SenderOrderTab): Order[] {
  if (tab === "PENDING") {
    return orders.filter((o) => o.status === "PENDING");
  }
  if (tab === "ACTIVE") {
    return orders.filter((o) => SENDER_ACTIVE_STATUSES.includes(o.status as OrderStatus));
  }
  return orders.filter((o) => o.status === "COMPLETED" || o.status === "CANCELLED");
}

function formatPrice(price: number, currency: string): string {
  return `${Number(price).toLocaleString("uz-UZ")} ${currency}`;
}

function formatWeightTonnes(weight: number): string {
  const kg = Number(weight) * 1000;
  return kg >= 1000 ? `${(kg / 1000).toFixed(1)} t` : `${Math.round(kg)} kg`;
}

export const OrderListPage: React.FC = () => {
  const { toast } = useToast();
  const [tab, setTab] = useState<SenderOrderTab>("PENDING");
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true);
      else setRefreshing(true);
      try {
        setError(null);
        const data = await fetchSenderOrders();
        setOrders(data);
      } catch (ex: unknown) {
        const msg = ex instanceof Error ? ex.message : "Buyurtmalar yuklanmadi";
        setError(msg);
        toast(msg, "error");
        setOrders([]);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [toast]
  );

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => filterByTab(orders, tab), [orders, tab]);

  const tabCounts = useMemo(
    () =>
      TABS.reduce(
        (acc, t) => {
          acc[t.key] = filterByTab(orders, t.key).length;
          return acc;
        },
        {} as Record<SenderOrderTab, number>
      ),
    [orders]
  );

  return (
    <div className="space-y-4 pb-6">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-slate-300">Mening buyurtmalarim</h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => load(true)}
            disabled={refreshing}
            className="p-2 rounded-xl text-slate-400 hover:text-cyan-400 hover:bg-white/5"
            aria-label="Yangilash"
          >
            <RefreshCw size={18} className={refreshing ? "animate-spin" : ""} />
          </button>
          <Link
            to="/sender/orders/create"
            className="flex items-center gap-1 rounded-xl px-3 py-1.5 text-xs font-semibold bg-cyan-500/15 text-cyan-300 ring-1 ring-cyan-500/30"
          >
            <Plus size={14} />
            Yangi
          </Link>
        </div>
      </div>

      <div className="flex gap-1 rounded-2xl bg-slate-900/60 p-1 ring-1 ring-white/10">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`flex-1 rounded-xl py-2 text-xs font-semibold transition-colors ${
              tab === t.key
                ? "bg-cyan-500/20 text-cyan-300"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {t.label}
            {tabCounts[t.key] > 0 && (
              <span className="ml-1 opacity-70">({tabCounts[t.key]})</span>
            )}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 rounded-2xl" />
          ))}
        </div>
      ) : error ? (
        <div className="mobile-card text-center">
          <p className="text-rose-400 text-sm">{error}</p>
          <button
            type="button"
            onClick={() => load()}
            className="mt-3 text-sm text-cyan-400 font-medium"
          >
            Qayta urinish
          </button>
        </div>
      ) : filtered.length === 0 ? (
        <div className="mobile-card text-center py-8">
          <Package size={32} className="mx-auto text-slate-600 mb-3" />
          <p className="text-sm text-slate-500">Bu bo&apos;limda buyurtmalar yo&apos;q</p>
          <Link
            to="/sender/orders/create"
            className="inline-flex items-center gap-1 mt-4 text-sm font-medium text-cyan-400"
          >
            <Plus size={16} />
            Birinchi buyurtmani yaratish
          </Link>
        </div>
      ) : (
        <ul className="space-y-3">
          {filtered.map((order) => (
            <li key={order.id}>
              <Link
                to={`/sender/orders/${order.id}`}
                className="block rounded-2xl bg-slate-900/50 ring-1 ring-white/10 p-4 hover:ring-cyan-500/30 transition-all"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-slate-100 truncate">{order.cargo_name}</p>
                    <p className="text-xs text-slate-500 mt-1">
                      #{order.id} · {formatWeightTonnes(order.weight)}
                      {order.volume != null ? ` · ${order.volume} m³` : ""}
                    </p>
                    <p className="text-sm text-cyan-400 mt-1 font-medium">
                      {formatPrice(order.price, order.currency)}
                    </p>
                  </div>
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    <OrderStatusBadge status={order.status} />
                    <ChevronRight size={18} className="text-slate-600" />
                  </div>
                </div>
                {order.waypoints.length > 0 && (
                  <p className="text-xs text-slate-500 mt-2 truncate">
                    {order.waypoints[0]?.address}
                    {order.waypoints.length > 1
                      ? ` → ${order.waypoints[order.waypoints.length - 1]?.address}`
                      : ""}
                  </p>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}

      {refreshing && !loading && (
        <p className="text-center text-xs text-slate-600 flex items-center justify-center gap-1">
          <Loader2 size={12} className="animate-spin" />
          Yangilanmoqda...
        </p>
      )}
    </div>
  );
};
