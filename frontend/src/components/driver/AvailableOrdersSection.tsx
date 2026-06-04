import React, { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { fetchAvailableOrders } from "../../services/driverApi";
import { createOrderOffer } from "../../services/orderApi";
import { useLocation } from "../../context/LocationContext";
import { useToast } from "../ui/Toast";
import { Skeleton } from "../ui/Skeleton";
import { DriverOrderCard } from "./DriverOrderCard";
import type { Order } from "../../types/order";

export const AvailableOrdersSection: React.FC = () => {
  const { toast } = useToast();
  const { coords } = useLocation();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const data = await fetchAvailableOrders();
      setOrders(data);
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Buyurtmalar yuklanmadi", "error");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const handleOffer = async (order: Order) => {
    setBusyId(order.id);
    try {
      await createOrderOffer(order.id, {
        offered_price: Number(order.price),
        currency: order.currency,
        comment: "Ro'yxat narxida taklif",
        driver_latitude: coords?.latitude ?? null,
        driver_longitude: coords?.longitude ?? null,
      });
      toast("Taklif yuborildi", "success");
      await load(true);
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Taklif xatolik", "error");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="flex flex-col flex-1 min-h-0">
      <div className="flex items-center justify-between gap-2 mb-4 sticky top-0 z-10 bg-slate-900/95 backdrop-blur-sm py-1 -mx-1 px-1">
        <h2 className="text-sm font-bold text-white leading-snug">
          Menga mos keluvchi yangi buyurtmalar
        </h2>
        <button
          type="button"
          onClick={() => load(true)}
          disabled={loading || refreshing}
          className="flex h-9 w-9 items-center justify-center rounded-xl bg-slate-800/80 border border-white/10 text-slate-300 hover:text-white hover:bg-slate-700/80 transition disabled:opacity-50"
          aria-label="Yangilash"
        >
          <RefreshCw
            size={18}
            className={refreshing ? "animate-spin text-cyan-400" : ""}
          />
        </button>
      </div>

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-52 w-full rounded-2xl" />
          <Skeleton className="h-52 w-full rounded-2xl" />
        </div>
      ) : orders.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-600/40 bg-slate-800/30 py-16 text-center">
          <p className="text-sm text-slate-400">Hozircha mos buyurtma yo&apos;q</p>
        </div>
      ) : (
        <ul className="space-y-4 pb-2 list-none m-0 p-0">
          {orders.map((order) => (
            <li key={order.id}>
              <DriverOrderCard
                order={order}
                busy={busyId === order.id}
                onOffer={handleOffer}
              />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
};
