import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, PackageOpen, RefreshCw, Truck } from "lucide-react";
import { acceptOrderDirectApi, createOrderOffer, fetchPendingOrders } from "../../services/orderApi";
import { fetchTruckTypes } from "../../services/driverApi";
import { useLocation } from "../../context/LocationContext";
import { useToast } from "../ui/Toast";
import { Skeleton } from "../ui/Skeleton";
import { DriverOrderCard } from "./DriverOrderCard";
import { OfferModal } from "./OfferModal";
import type { Order } from "../../types/order";

export type DriverOrdersFilterMode = "all" | "my_truck";

export interface DriverOrdersListProps {
  title?: string;
}

const EMPTY_MESSAGES: Record<DriverOrdersFilterMode, string> = {
  all: "Hozircha faol (pending) buyurtmalar mavjud emas",
  my_truck: "Hozircha sizning mashinangizga mos buyurtmalar topilmadi",
};

export const DriverOrdersList: React.FC<DriverOrdersListProps> = ({
  title = "Yangi buyurtmalar",
}) => {
  const navigate = useNavigate();
  const { toast } = useToast();
  const { coords } = useLocation();
  const [filterMode, setFilterMode] = useState<DriverOrdersFilterMode>("all");
  const [orders, setOrders] = useState<Order[]>([]);
  const [truckTypesMap, setTruckTypesMap] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);

  const filterByTruck = filterMode === "my_truck";
  const emptyMessage = EMPTY_MESSAGES[filterMode];

  const load = useCallback(
    async (silent = false) => {
      if (!silent) setLoading(true);
      else setRefreshing(true);
      try {
        setLoadError(null);
        const pending = await fetchPendingOrders(filterByTruck);
        setOrders(pending);
      } catch (ex: unknown) {
        const msg = ex instanceof Error ? ex.message : "Buyurtmalar yuklanmadi";
        setLoadError(msg);
        toast(msg, "error");
        setOrders([]);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [toast, filterByTruck]
  );

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const loadTruckTypes = async () => {
      try {
        const types = await fetchTruckTypes();
        const map: Record<number, string> = {};
        types.forEach((t) => {
          map[t.id] = t.name;
        });
        setTruckTypesMap(map);
      } catch (err) {
        console.error("Failed to fetch truck types", err);
      }
    };
    loadTruckTypes();
  }, []);

  const handleAcceptClick = async (order: Order) => {
    const confirm = window.confirm(
      `Siz ushbu buyurtmani ${Number(order.price).toLocaleString()} ${order.currency} narxi va ko'rsatilgan shartlari bilan qabul qilishga rozimisiz?`
    );
    if (!confirm) return;

    setBusyId(order.id);
    try {
      await acceptOrderDirectApi(order.id);
      toast("Buyurtma muvaffaqiyatli qabul qilindi!", "success");
      navigate("/driver/trips");
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Xatolik yuz berdi", "error");
    } finally {
      setBusyId(null);
    }
  };

  const handleOfferClick = (order: Order) => {
    setSelectedOrder(order);
  };

  const submitOffer = async (price: number, comment: string) => {
    if (!selectedOrder) return;
    setBusyId(selectedOrder.id);
    try {
      await createOrderOffer(selectedOrder.id, {
        offered_price: price,
        currency: selectedOrder.currency,
        comment: comment || "Yangi taklif",
        driver_latitude: coords?.latitude ?? null,
        driver_longitude: coords?.longitude ?? null,
      });
      toast("Taklif yuborildi", "success");
      setSelectedOrder(null);
      await load(true);
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Taklif xatolik", "error");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="flex flex-col flex-1 min-h-[50vh] w-full">
      <div className="flex items-center justify-between gap-2 mb-3">
        <h2 className="text-sm font-bold text-white leading-snug">{title}</h2>
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

      <div
        className="mb-4 flex rounded-xl bg-slate-800/80 p-1 border border-white/10"
        role="tablist"
        aria-label="Buyurtmalar filtri"
      >
        <button
          type="button"
          role="tab"
          aria-selected={filterMode === "all"}
          onClick={() => setFilterMode("all")}
          className={`flex-1 rounded-lg py-2.5 px-3 text-xs font-semibold transition ${
            filterMode === "all"
              ? "bg-cyan-600/90 text-white shadow-md shadow-cyan-900/30"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          Barcha yuklar
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={filterMode === "my_truck"}
          onClick={() => setFilterMode("my_truck")}
          className={`flex-1 flex items-center justify-center gap-1.5 rounded-lg py-2.5 px-3 text-xs font-semibold transition ${
            filterMode === "my_truck"
              ? "bg-emerald-600/90 text-white shadow-md shadow-emerald-900/30"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Truck size={14} aria-hidden />
          Mening mashinam
        </button>
      </div>

      {filterMode === "my_truck" && !loading && (
        <p className="text-[11px] text-slate-500 -mt-2 mb-3 px-1">
          Faqat profilingizdagi mashina turiga mos pending buyurtmalar
        </p>
      )}

      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <Loader2 size={32} className="animate-spin text-cyan-400" />
          <p className="text-sm text-slate-400">Yuklanmoqda...</p>
          <div className="w-full space-y-4 mt-4">
            <Skeleton className="h-52 w-full rounded-2xl" />
            <Skeleton className="h-52 w-full rounded-2xl" />
          </div>
        </div>
      ) : orders.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center min-h-[40vh] rounded-2xl border border-dashed border-slate-500/50 bg-slate-800/60 px-6 py-12 text-center">
          <PackageOpen size={44} className="text-slate-500 mb-4 shrink-0" aria-hidden />
          <p className="text-base font-semibold text-slate-100">{emptyMessage}</p>
          {loadError ? (
            <p className="text-xs text-rose-400/90 mt-3 max-w-xs">{loadError}</p>
          ) : (
            <p className="text-xs text-slate-400 mt-3 max-w-xs leading-relaxed">
              {filterMode === "my_truck"
                ? "Boshqa mashina turlari uchun «Barcha yuklar» bo‘limiga o‘ting yoki ro‘yxatni yangilang."
                : "Yangi buyurtmalar paydo bo‘lganda shu yerda ko‘rinadi."}
            </p>
          )}
        </div>
      ) : (
        <ul className="space-y-4 pb-4 list-none m-0 p-0">
          {orders.map((order) => (
            <li key={order.id}>
              <DriverOrderCard
                order={order}
                busy={busyId === order.id}
                onOffer={handleOfferClick}
                onAccept={handleAcceptClick}
                truckTypeName={truckTypesMap[order.required_truck_type_id]}
              />
            </li>
          ))}
        </ul>
      )}

      <OfferModal
        isOpen={!!selectedOrder}
        onClose={() => setSelectedOrder(null)}
        onSubmit={submitOffer}
        orderPrice={selectedOrder?.price || 0}
        orderCurrency={selectedOrder?.currency || "UZS"}
        busy={busyId !== null}
      />
    </section>
  );
};
