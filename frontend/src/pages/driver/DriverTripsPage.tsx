import React, { useCallback, useEffect, useState } from "react";
import { fetchDriverTrips } from "../../services/driverApi";
import { useToast } from "../../components/ui/Toast";
import { Skeleton } from "../../components/ui/Skeleton";
import { DriverOrderCard } from "../../components/driver/DriverOrderCard";
import type { Order } from "../../types/order";

type TripScope = "current" | "completed" | "all";

const TABS: { id: TripScope; label: string }[] = [
  { id: "current", label: "Joriy" },
  { id: "completed", label: "Tugallangan" },
  { id: "all", label: "Barchasi" },
];

export const DriverTripsPage: React.FC = () => {
  const { toast } = useToast();
  const [scope, setScope] = useState<TripScope>("current");
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setOrders(await fetchDriverTrips(scope));
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Safarlar yuklanmadi", "error");
    } finally {
      setLoading(false);
    }
  }, [scope, toast]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-4 pb-6">
      <div className="flex gap-2 p-1 rounded-xl bg-slate-800/60 border border-white/5">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setScope(tab.id)}
            className={`flex-1 rounded-lg py-2 text-xs font-semibold transition ${
              scope === tab.id
                ? "bg-white/10 text-white"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-48 w-full rounded-2xl" />
          <Skeleton className="h-48 w-full rounded-2xl" />
        </div>
      ) : orders.length === 0 ? (
        <p className="text-center text-slate-400 py-12 text-sm">Safarlar topilmadi</p>
      ) : (
        <ul className="space-y-4 list-none m-0 p-0">
          {orders.map((order) => (
            <li key={order.id}>
              <DriverOrderCard order={order} showOfferButton={false} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
