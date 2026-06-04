import React, { useCallback, useEffect, useState } from "react";
import { Box, Scale, Send, Sparkles } from "lucide-react";
import { fetchDriverMe } from "../../services/driverApi";
import { createOrderOffer, fetchOrders } from "../../services/orderApi";
import { useLocation } from "../../context/LocationContext";
import { useToast } from "../ui/Toast";
import { Skeleton } from "../ui/Skeleton";
import { OrderWaypointChain } from "./OrderWaypointChain";
import type { Order } from "../../types/order";

export const AvailableOrdersSection: React.FC<{ compact?: boolean }> = ({ compact }) => {
  const { toast } = useToast();
  const { coords } = useLocation();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const me = await fetchDriverMe();
      const all = await fetchOrders({ status: "pending" });
      const matched = all.filter(
        (o) => !o.driver_id && o.required_truck_type_id === me.truck_type_id
      );
      setOrders(matched);
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Buyurtmalar yuklanmadi", "error");
    } finally {
      setLoading(false);
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
      await load();
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Taklif xatolik", "error");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section
      className={`rounded-2xl border border-white/5 bg-slate-800/60 backdrop-blur-md p-5 ${
        compact ? "mt-2" : "mt-6"
      }`}
    >
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-500/15">
            <Sparkles className="text-amber-400" size={18} />
          </div>
          <div>
            <h2 className="text-base font-bold text-white leading-tight">
              Menga mos keluvchi yangi buyurtmalar
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">Status: pending · mashina turiga mos</p>
          </div>
        </div>
        <button
          type="button"
          onClick={load}
          className="text-xs text-cyan-400 font-semibold px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 transition"
        >
          Yangilash
        </button>
      </div>

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-36 w-full rounded-2xl" />
          <Skeleton className="h-36 w-full rounded-2xl" />
        </div>
      ) : orders.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-600/50 bg-slate-900/40 py-12 text-center">
          <p className="text-sm text-slate-400">Hozircha mos buyurtma yo&apos;q</p>
          <p className="text-xs text-slate-600 mt-1">GPS yoqilgan bo&apos;lsa tezroq topasiz</p>
        </div>
      ) : (
        <div className="space-y-4">
          {orders.map((order) => (
            <article
              key={order.id}
              className="rounded-2xl border border-white/5 bg-slate-900/50 p-4 space-y-4 hover:border-cyan-500/25 transition shadow-lg shadow-black/20"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-bold text-white text-lg">{order.cargo_name}</p>
                  <div className="flex flex-wrap gap-4 mt-2 text-xs text-slate-400">
                    <span className="inline-flex items-center gap-1.5">
                      <Scale size={13} className="text-amber-400" />
                      {order.weight} t
                    </span>
                    {order.volume != null && (
                      <span className="inline-flex items-center gap-1.5">
                        <Box size={13} className="text-cyan-400" />
                        {order.volume} m³
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-right shrink-0">
                  <span className="text-lg font-bold text-emerald-400">
                    {Number(order.price).toLocaleString()}
                  </span>
                  <span className="block text-[10px] text-slate-500 uppercase">{order.currency}</span>
                </p>
              </div>

              <OrderWaypointChain waypoints={order.waypoints} />

              <button
                type="button"
                disabled={busyId === order.id}
                onClick={() => handleOffer(order)}
                className="w-full inline-flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-emerald-600 to-cyan-600 py-3 text-sm font-semibold text-white disabled:opacity-50 shadow-lg shadow-emerald-900/30"
              >
                <Send size={17} />
                {busyId === order.id ? "Yuborilmoqda…" : "Taklif berish"}
              </button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
};
