import React, { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Loader2, Trash2, Check, X, Edit2 } from "lucide-react";
import {
  deleteSenderOrder,
  fetchSenderOrder,
  fetchSenderOrderOffers,
  patchSenderOrderOffer,
  updateSenderOrder,
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

  // Edit states
  const [showEditModal, setShowEditModal] = useState(false);
  const [editCargoName, setEditCargoName] = useState("");
  const [editWeightKg, setEditWeightKg] = useState("");
  const [editVolume, setEditVolume] = useState("");
  const [editPrice, setEditPrice] = useState("");
  const [updating, setUpdating] = useState(false);

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

      // Initialize edit fields
      setEditCargoName(orderData.cargo_name || "");
      setEditWeightKg(String(Math.round(Number(orderData.weight) * 1000)));
      setEditVolume(orderData.volume != null ? String(orderData.volume) : "");
      const priceStr = new Intl.NumberFormat("fr-FR").format(Number(orderData.price));
      setEditPrice(priceStr);
    } catch (ex: unknown) {
      const msg = ex instanceof Error ? ex.message : "Ma'lumot yuklanmadi";
      setError(msg);
      toast(msg, "error");
    } finally {
      setLoading(false);
    }
  }, [pk, toast]);

  const handleEditPriceChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const rawValue = e.target.value.replace(/\D/g, "");
    if (!rawValue) {
      setEditPrice("");
      return;
    }
    const formatted = new Intl.NumberFormat("fr-FR").format(Number(rawValue));
    setEditPrice(formatted);
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editCargoName.trim()) {
      toast("Yuk nomi majburiy", "error");
      return;
    }
    const weight = Number(editWeightKg);
    if (!weight || weight <= 0) {
      toast("Og'irlik 0 dan katta bo'lishi kerak", "error");
      return;
    }
    const parsedPrice = Number(editPrice.replace(/\s/g, ""));
    if (!parsedPrice || parsedPrice <= 0) {
      toast("Narx 0 dan katta bo'lishi kerak", "error");
      return;
    }

    setUpdating(true);
    try {
      await updateSenderOrder(pk, {
        cargo_name: editCargoName.trim(),
        weight: weight / 1000,
        volume: editVolume ? Number(editVolume) : null,
        price: parsedPrice,
      });
      toast("Buyurtma yangilandi", "success");
      setShowEditModal(false);
      await load();
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Yangilashda xatolik", "error");
    } finally {
      setUpdating(false);
    }
  };

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
      <div className="rounded-2xl border border-white/5 bg-slate-800/60 backdrop-blur-md p-6 shadow-lg text-center mx-4">
        <p className="text-rose-400 text-sm">{error ?? "Buyurtma topilmadi"}</p>
        <button
          type="button"
          onClick={() => navigate("/sender/orders")}
          className="mt-4 rounded-xl bg-slate-700/50 px-4 py-2 text-sm font-semibold text-cyan-400 transition hover:bg-slate-600"
        >
          Ro&apos;yxatga qaytish
        </button>
      </div>
    );
  }

  const orderStatusUpper = order?.status?.toUpperCase() ?? "";
  const canDelete = orderStatusUpper === "PENDING";
  const canEdit = orderStatusUpper === "PENDING";
  const canAcceptOffers = orderStatusUpper === "PENDING" && order.driver_id == null;

  return (
    <div className="space-y-4 pb-6 px-4 mt-4">
      <section className="rounded-2xl border border-white/5 bg-slate-800/60 backdrop-blur-md p-5 shadow-lg space-y-4">
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

        {canEdit && (
          <button
            type="button"
            onClick={() => setShowEditModal(true)}
            className="flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold text-cyan-400 bg-cyan-500/10 ring-1 ring-cyan-500/20 mb-2 transition active:scale-[0.99]"
          >
            <Edit2 size={16} />
            Buyurtmani tahrirlash
          </button>
        )}

        {canDelete && (
          <button
            type="button"
            onClick={() => setShowDeleteConfirm(true)}
            disabled={deleting}
            className="flex w-full items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-medium text-rose-400 bg-rose-500/10 ring-1 ring-rose-500/20 transition active:scale-[0.99]"
          >
            {deleting ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
            Buyurtmani o&apos;chirish
          </button>
        )}
      </section>

      <section className="rounded-2xl border border-white/5 bg-slate-800/60 backdrop-blur-md p-5 shadow-lg">
        <h3 className="text-sm font-semibold text-slate-300 mb-4">Marshrut</h3>
        <SenderWaypointTimeline waypoints={order.waypoints} />
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-slate-300 ml-1">
          Haydovchi takliflari ({offers.length})
        </h3>

        {offers.length === 0 ? (
          <div className="rounded-2xl border border-white/5 bg-slate-800/60 backdrop-blur-md p-8 shadow-lg text-center">
            <p className="text-sm text-slate-400">Hozircha takliflar yo&apos;q</p>
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
                    <div className="flex gap-2 pt-2">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => handleOfferAction(offer.id, "accepted")}
                        className="flex-1 flex items-center justify-center gap-1.5 rounded-xl py-2.5 text-xs font-semibold bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow-lg shadow-emerald-900/20 disabled:opacity-50 transition active:scale-[0.99]"
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
                        className="flex-1 flex items-center justify-center gap-1.5 rounded-xl py-2.5 text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20 disabled:opacity-50 transition hover:bg-rose-500/20 active:scale-[0.99]"
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

      {showEditModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-slate-900 p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-white">Buyurtmani tahrirlash</h3>
            <form onSubmit={handleUpdate} className="space-y-4">
              <div>
                <label className="block text-xs text-slate-400 mb-1">Yuk nomi *</label>
                <input
                  type="text"
                  className="glass-input w-full text-slate-100"
                  value={editCargoName}
                  onChange={(e) => setEditCargoName(e.target.value)}
                  maxLength={200}
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Og&apos;irlik (kg) *</label>
                  <input
                    type="number"
                    min="1"
                    step="1"
                    className="glass-input w-full text-slate-100"
                    value={editWeightKg}
                    onChange={(e) => setEditWeightKg(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs text-slate-400 mb-1">Hajm (m³)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.1"
                    className="glass-input w-full text-slate-100"
                    value={editVolume}
                    onChange={(e) => setEditVolume(e.target.value)}
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs text-slate-400 mb-1">Narx (so&apos;m) *</label>
                <input
                  type="text"
                  inputMode="numeric"
                  className="glass-input w-full text-slate-100"
                  value={editPrice}
                  onChange={handleEditPriceChange}
                  required
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  disabled={updating}
                  className="flex-1 rounded-xl border border-white/10 bg-slate-800 text-slate-300 py-2.5 text-sm font-semibold hover:bg-slate-700"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={updating}
                  className="flex-1 flex items-center justify-center gap-1.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 text-white py-2.5 text-sm font-semibold hover:opacity-90 disabled:opacity-50"
                >
                  {updating ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    "Saqlash"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

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
