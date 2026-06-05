import React, { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Loader2, Trash2, Check, X } from "lucide-react";
import {
  deleteSenderOrder,
  fetchSenderOrder,
  fetchSenderOrderOffers,
  patchSenderOrderOffer,
} from "../../services/senderApi";
import type { OrderOffer } from "../../services/orderApi";
import { OrderStatusBadge } from "../../components/sender/OrderStatusBadge";
import { SenderWaypointTimeline } from "../../components/sender/SenderWaypointTimeline";
import { ConfirmModal } from "../../components/mobile/ConfirmModal";
import { Skeleton } from "../../components/ui/Skeleton";
import { useToast } from "../../components/ui/Toast";
import type { Order } from "../../types/order";

const OFFER_STATUS_LABEL: Record<string, string> = {
  pending: "Kutilmoqda",
  seen: "Ko'rilgan",
  accepted: "Qabul qilingan",
  rejected: "Rad etilgan",
  cancelled: "Bekor qilingan",
  expired: "Muddati tugagan",
  outbid: "Ortiqcha taklif",
};

function formatPrice(price: number, currency: string): string {
  return `${Number(price).toLocaleString("uz-UZ")} ${currency}`;
}

export const OrderDetailPage: React.FC = () => {
  const { orderId } = useParams<{ orderId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();

  const pk = Number(orderId);
  const [order, setOrder] = useState<Order | null>(null);
  const [offers, setOffers] = useState<OrderOffer[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyOfferId, setBusyOfferId] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!pk || Number.isNaN(pk)) {
      setError("Noto'g'ri buyurtma ID");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [orderData, offersData] = await Promise.all([
        fetchSenderOrder(pk),
        fetchSenderOrderOffers(pk),
      ]);
      setOrder(orderData);
      setOffers(offersData);
    } catch (ex: unknown) {
      const msg = ex instanceof Error ? ex.message : "Ma'lumot yuklanmadi";
      setError(msg);
      toast(msg, "error");
    } finally {
      setLoading(false);
    }
  }, [pk, toast]);

  useEffect(() => {
    load();
  }, [load]);

  const handleOfferAction = async (offerId: number, status: "accepted" | "rejected") => {
    setBusyOfferId(offerId);
    try {
      await patchSenderOrderOffer(offerId, { status });
      toast(status === "accepted" ? "Taklif qabul qilindi" : "Taklif rad etildi", "success");
      await load();
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Amal bajarilmadi", "error");
    } finally {
      setBusyOfferId(null);
    }
  };

  const handleDelete = async () => {
    if (!pk) return;
    setDeleting(true);
    try {
      await deleteSenderOrder(pk);
      toast("Buyurtma o'chirildi", "success");
      navigate("/sender/orders");
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "O'chirish xatolik", "error");
    } finally {
      setDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 rounded-2xl" />
        <Skeleton className="h-48 rounded-2xl" />
        <Skeleton className="h-32 rounded-2xl" />
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="mobile-card text-center">
        <p className="text-rose-400 text-sm">{error ?? "Buyurtma topilmadi"}</p>
        <button
          type="button"
          onClick={() => navigate("/sender/orders")}
          className="mt-3 text-sm text-cyan-400"
        >
          Ro&apos;yxatga qaytish
        </button>
      </div>
    );
  }

  const canDelete = order.status === "PENDING";
  const canAcceptOffers = order.status === "PENDING" && order.driver_id == null;

  return (
    <div className="space-y-4 pb-6">
      <section className="mobile-card space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="!mb-0">{order.cargo_name}</h3>
            <p className="text-xs text-slate-500 mt-1">Buyurtma #{order.id}</p>
          </div>
          <OrderStatusBadge status={order.status} />
        </div>

        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-xs text-slate-500">Og&apos;irlik</dt>
            <dd className="text-slate-200 font-medium">
              {Math.round(Number(order.weight) * 1000).toLocaleString("uz-UZ")} kg
            </dd>
          </div>
          {order.volume != null && (
            <div>
              <dt className="text-xs text-slate-500">Hajm</dt>
              <dd className="text-slate-200 font-medium">{order.volume} m³</dd>
            </div>
          )}
          <div className="col-span-2">
            <dt className="text-xs text-slate-500">Narx</dt>
            <dd className="text-cyan-400 font-semibold text-lg">
              {formatPrice(order.price, order.currency)}
            </dd>
          </div>
        </dl>

        {canDelete && (
          <button
            type="button"
            onClick={() => setShowDeleteConfirm(true)}
            disabled={deleting}
            className="flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-medium text-rose-400 bg-rose-500/10 ring-1 ring-rose-500/20"
          >
            {deleting ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
            Buyurtmani o&apos;chirish
          </button>
        )}
      </section>

      <section className="mobile-card">
        <h3 className="text-sm font-semibold text-slate-300 mb-3">Marshrut</h3>
        <SenderWaypointTimeline waypoints={order.waypoints} />
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-slate-300">
          Haydovchi takliflari ({offers.length})
        </h3>

        {offers.length === 0 ? (
          <div className="mobile-card text-center py-6">
            <p className="text-sm text-slate-500">Hozircha takliflar yo&apos;q</p>
          </div>
        ) : (
          <ul className="space-y-3">
            {offers.map((offer) => {
              const isPending = offer.status === "pending" || offer.status === "seen";
              const busy = busyOfferId === offer.id;

              return (
                <li
                  key={offer.id}
                  className="rounded-2xl bg-slate-900/50 ring-1 ring-white/10 p-4 space-y-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-semibold text-cyan-400">
                        {formatPrice(offer.offered_price, offer.currency)}
                      </p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Haydovchi #{offer.driver_id} ·{" "}
                        {OFFER_STATUS_LABEL[offer.status] ?? offer.status}
                      </p>
                    </div>
                  </div>

                  {offer.comment && (
                    <p className="text-sm text-slate-400 bg-slate-800/50 rounded-lg px-3 py-2">
                      {offer.comment}
                    </p>
                  )}

                  {offer.distance_to_pickup_km != null && (
                    <p className="text-xs text-slate-600">
                      Yuklash nuqtasigacha: ~{Number(offer.distance_to_pickup_km).toFixed(1)} km
                    </p>
                  )}

                  {canAcceptOffers && isPending && (
                    <div className="flex gap-2 pt-1">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => handleOfferAction(offer.id, "accepted")}
                        className="flex-1 flex items-center justify-center gap-1.5 rounded-xl py-2 text-xs font-semibold bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30 disabled:opacity-50"
                      >
                        {busy ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <Check size={14} />
                        )}
                        Qabul qilish
                      </button>
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => handleOfferAction(offer.id, "rejected")}
                        className="flex-1 flex items-center justify-center gap-1.5 rounded-xl py-2 text-xs font-semibold bg-rose-500/15 text-rose-300 ring-1 ring-rose-500/30 disabled:opacity-50"
                      >
                        {busy ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <X size={14} />
                        )}
                        Rad etish
                      </button>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <ConfirmModal
        open={showDeleteConfirm}
        title="Buyurtmani o'chirish"
        message="Buyurtma va barcha takliflar o'chiriladi. Haydovchilarga xabar yuboriladi. Davom etasizmi?"
        confirmLabel={deleting ? "O'chirilmoqda..." : "O'chirish"}
        cancelLabel="Bekor qilish"
        danger
        onConfirm={handleDelete}
        onCancel={() => !deleting && setShowDeleteConfirm(false)}
      />
    </div>
  );
};
