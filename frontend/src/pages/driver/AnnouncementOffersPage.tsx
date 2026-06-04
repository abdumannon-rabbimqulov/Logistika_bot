import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  fetchAnnouncement,
  fetchAnnouncementOffers,
  updateOffer,
} from "../../services/driverApi";
import { useToast } from "../../components/ui/Toast";
import { Modal } from "../../components/ui/Modal";
import { Skeleton } from "../../components/ui/Skeleton";
import type { AnnouncementOffer } from "../../types/driver";
import { Package, Scale, Box, Banknote, Check, X, MessageSquare } from "lucide-react";

export const AnnouncementOffersPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const annId = Number(id);
  const { toast } = useToast();

  const [announcement, setAnnouncement] = useState<Awaited<ReturnType<typeof fetchAnnouncement>> | null>(null);
  const [offers, setOffers] = useState<AnnouncementOffer[]>([]);
  const [loading, setLoading] = useState(true);
  const [counterOffer, setCounterOffer] = useState<AnnouncementOffer | null>(null);
  const [counterPrice, setCounterPrice] = useState("");
  const [counterComment, setCounterComment] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    if (!annId) return;
    setLoading(true);
    try {
      const [a, o] = await Promise.all([fetchAnnouncement(annId), fetchAnnouncementOffers(annId)]);
      setAnnouncement(a);
      setOffers(o);
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Yuklanmadi", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [annId]);

  const patchOffer = async (offerId: number, body: Parameters<typeof updateOffer>[1]) => {
    setBusy(true);
    try {
      await updateOffer(offerId, body);
      toast("Yangilandi", "success");
      setCounterOffer(null);
      await load();
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Xatolik", "error");
    } finally {
      setBusy(false);
    }
  };

  const submitCounter = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!counterOffer || !counterPrice) return;
    await patchOffer(counterOffer.id, {
      counter_price: Number(counterPrice),
      counter_comment: counterComment || undefined,
      status: "pending",
    });
  };

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-8">
      {announcement && (
        <div className="rounded-2xl border border-slate-700/80 bg-slate-800/60 p-4">
          <p className="text-lg font-bold text-white">
            {Number(announcement.price).toLocaleString()} {announcement.currency}
          </p>
          <p className="text-sm text-slate-400 mt-1">{announcement.description || "Safar e'loni"}</p>
        </div>
      )}

      <h3 className="text-sm font-semibold text-slate-300">Mijoz takliflari ({offers.length})</h3>

      {offers.length === 0 ? (
        <p className="text-center text-slate-500 py-10 text-sm">Hali taklif yo&apos;q</p>
      ) : (
        offers.map((o) => (
          <article
            key={o.id}
            className="rounded-2xl border border-slate-700/80 bg-slate-800/80 p-4 space-y-3"
          >
            <div className="flex items-start gap-2">
              <Package className="text-cyan-400 shrink-0" size={20} />
              <div>
                <p className="font-bold text-white">{o.cargo_name}</p>
                {o.cargo_description && (
                  <p className="text-xs text-slate-400 mt-0.5">{o.cargo_description}</p>
                )}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm text-slate-300">
              {o.cargo_weight != null && (
                <span className="flex items-center gap-1">
                  <Scale size={14} /> {o.cargo_weight} t
                </span>
              )}
              {o.cargo_volume != null && (
                <span className="flex items-center gap-1">
                  <Box size={14} /> {o.cargo_volume} m³
                </span>
              )}
            </div>
            <p className="flex items-center gap-2 text-emerald-300 font-semibold">
              <Banknote size={18} />
              {Number(o.offered_price).toLocaleString()} {o.currency}
            </p>
            {o.counter_price != null && (
              <p className="text-sm text-amber-300">
                Qarshi taklif: {Number(o.counter_price).toLocaleString()} {o.currency}
              </p>
            )}
            <span className="text-xs uppercase tracking-wide text-slate-500">{o.status}</span>

            {o.status === "pending" || o.status === "seen" ? (
              <div className="flex flex-wrap gap-2 pt-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => patchOffer(o.id, { status: "accepted" })}
                  className="flex-1 inline-flex items-center justify-center gap-1 rounded-lg bg-emerald-600 py-2.5 text-sm font-semibold text-white min-w-[100px]"
                >
                  <Check size={16} /> Qabul
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => patchOffer(o.id, { status: "rejected" })}
                  className="flex-1 inline-flex items-center justify-center gap-1 rounded-lg border border-rose-500/50 py-2.5 text-sm text-rose-300 min-w-[100px]"
                >
                  <X size={16} /> Rad
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => {
                    setCounterOffer(o);
                    setCounterPrice(String(o.offered_price));
                    setCounterComment("");
                  }}
                  className="w-full inline-flex items-center justify-center gap-1 rounded-lg border border-cyan-500/40 py-2.5 text-sm text-cyan-300"
                >
                  <MessageSquare size={16} /> Qarshi taklif
                </button>
              </div>
            ) : null}
          </article>
        ))
      )}

      <Modal
        open={counterOffer !== null}
        onClose={() => setCounterOffer(null)}
        title="Qarshi taklif"
      >
        <form onSubmit={submitCounter} className="space-y-4">
          <div>
            <label className="text-xs text-slate-400">Yangi narx</label>
            <input
              type="number"
              className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-white"
              value={counterPrice}
              onChange={(e) => setCounterPrice(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="text-xs text-slate-400">Izoh</label>
            <textarea
              rows={3}
              className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-white"
              value={counterComment}
              onChange={(e) => setCounterComment(e.target.value)}
            />
          </div>
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-xl bg-cyan-600 py-3 font-semibold text-white"
          >
            Yuborish (PATCH /offers/{counterOffer?.id})
          </button>
        </form>
      </Modal>
    </div>
  );
};
