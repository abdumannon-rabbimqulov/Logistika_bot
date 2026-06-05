import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, Plus, Send } from "lucide-react";
import { fetchTruckTypes } from "../../services/driverApi";
import { createSenderOrder } from "../../services/senderApi";
import type { TruckType } from "../../types/auth";
import type { OrderCreatePayload } from "../../types/order";
import {
  WaypointFormRow,
  createWaypoint,
  type WaypointFormValues,
} from "../../components/WaypointFormRow";
import { useToast } from "../../components/ui/Toast";
import { initTelegramWebApp } from "../../auth/telegram";

function parseDisplayPrice(displayPrice: string): number {
  return Number(displayPrice.replace(/\s/g, ""));
}

function validateForm(
  cargoName: string,
  weightKg: string,
  price: string,
  truckTypeId: string,
  waypoints: WaypointFormValues[]
): string | null {
  if (!cargoName.trim()) return "Yuk nomi majburiy";
  const w = Number(weightKg);
  if (!w || w <= 0) return "Og'irlik 0 dan katta bo'lishi kerak";
  const p = parseDisplayPrice(price);
  if (!p || p <= 0) return "Narx 0 dan katta bo'lishi kerak";
  if (!truckTypeId) return "Mashina turini tanlang";
  if (waypoints.length < 2) return "Kamida 2 ta marshrut nuqtasi kerak";

  const hasPickup = waypoints.some((w) => w.waypoint_type === "pickup");
  const hasDelivery = waypoints.some((w) => w.waypoint_type === "delivery");
  if (!hasPickup || !hasDelivery) return "Kamida bitta yuklash va bitta tushirish nuqtasi bo'lishi kerak";

  for (let i = 0; i < waypoints.length; i++) {
    if (!waypoints[i].address.trim()) return `Nuqta #${i + 1} manzili majburiy`;
  }

  return null;
}

function buildPayload(
  cargoName: string,
  weightKg: string,
  volume: string,
  price: string,
  truckTypeId: string,
  waypoints: WaypointFormValues[]
): OrderCreatePayload {
  const sorted = [...waypoints];

  return {
    cargo_name: cargoName.trim(),
    weight: Number(weightKg) / 1000,
    volume: volume ? Number(volume) : null,
    required_truck_type_id: Number(truckTypeId),
    price: parseDisplayPrice(price),
    currency: "UZS",
    waypoints: sorted.map((wp, i) => ({
      sequence: i + 1,
      waypoint_type: wp.waypoint_type,
      address: wp.address.trim(),
      note: wp.note.trim() || null,
      latitude: wp.latitude ?? undefined,
      longitude: wp.longitude ?? undefined,
    })),
  };
}

export const OrderCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [cargoName, setCargoName] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [volume, setVolume] = useState("");
  const [price, setPrice] = useState("");
  const [truckTypeId, setTruckTypeId] = useState("");
  const [waypoints, setWaypoints] = useState<WaypointFormValues[]>([
    createWaypoint("pickup"),
    createWaypoint("delivery"),
  ]);

  const [truckTypes, setTruckTypes] = useState<TruckType[]>([]);
  const [loadingTrucks, setLoadingTrucks] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    initTelegramWebApp();
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadingTrucks(true);
      try {
        const list = await fetchTruckTypes();
        if (!cancelled) {
          setTruckTypes(list.filter((t) => t.is_active));
        }
      } catch (ex: unknown) {
        if (!cancelled) {
          toast(ex instanceof Error ? ex.message : "Mashina turlari yuklanmadi", "error");
        }
      } finally {
        if (!cancelled) setLoadingTrucks(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [toast]);

  const updateWaypoint = (localId: string, next: WaypointFormValues) => {
    setWaypoints((prev) => prev.map((w) => (w.localId === localId ? next : w)));
  };

  const removeWaypoint = (localId: string) => {
    setWaypoints((prev) => prev.filter((w) => w.localId !== localId));
  };

  const handlePriceChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const rawValue = e.target.value.replace(/\D/g, "");
    if (!rawValue) {
      setPrice("");
      return;
    }
    const formatted = new Intl.NumberFormat("fr-FR").format(Number(rawValue));
    setPrice(formatted);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const err = validateForm(cargoName, weightKg, price, truckTypeId, waypoints);
    if (err) {
      setFormError(err);
      return;
    }
    setFormError(null);
    setSubmitting(true);

    try {
      const payload = buildPayload(cargoName, weightKg, volume, price, truckTypeId, waypoints);
      const order = await createSenderOrder(payload);
      toast("Buyurtma yaratildi", "success");
      navigate(`/sender/orders/${order.id}`);
    } catch (ex: unknown) {
      const msg = ex instanceof Error ? ex.message : "Buyurtma yaratilmadi";
      setFormError(msg);
      toast(msg, "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 pb-6">
      <section className="mobile-card space-y-3">
        <h3 className="!mb-0">Yuk ma&apos;lumotlari</h3>

        <div>
          <label className="block text-xs text-slate-500 mb-1">Yuk nomi *</label>
          <input
            type="text"
            className="glass-input w-full"
            placeholder="Masalan: Sement, mebel..."
            value={cargoName}
            onChange={(e) => setCargoName(e.target.value)}
            maxLength={200}
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Og&apos;irlik (kg) *</label>
            <input
              type="number"
              min="1"
              step="1"
              className="glass-input w-full"
              placeholder="20000"
              value={weightKg}
              onChange={(e) => setWeightKg(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Hajm (m³)</label>
            <input
              type="number"
              min="0"
              step="0.1"
              className="glass-input w-full"
              placeholder="30"
              value={volume}
              onChange={(e) => setVolume(e.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="block text-xs text-slate-500 mb-1">Narx (so&apos;m) *</label>
          <input
            type="text"
            inputMode="numeric"
            className="glass-input w-full"
            placeholder="4 500 000"
            value={price}
            onChange={handlePriceChange}
          />
        </div>

        <div>
          <label className="block text-xs text-slate-500 mb-1">Kerakli mashina turi *</label>
          {loadingTrucks ? (
            <p className="text-xs text-slate-500 flex items-center gap-2">
              <Loader2 size={14} className="animate-spin" /> Yuklanmoqda...
            </p>
          ) : (
            <select
              className="glass-input w-full"
              value={truckTypeId}
              onChange={(e) => setTruckTypeId(e.target.value)}
            >
              <option value="">Tanlang...</option>
              {truckTypes.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} (max {t.max_weight}t / {t.max_volume}m³)
                </option>
              ))}
            </select>
          )}
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200">Marshrut nuqtalari</h3>
          <button
            type="button"
            onClick={() => setWaypoints((prev) => [...prev, createWaypoint("transit")])}
            className="flex items-center gap-1 text-xs font-medium text-cyan-400 hover:text-cyan-300"
          >
            <Plus size={14} />
            Nuqta qo&apos;shish
          </button>
        </div>

        {waypoints.map((wp, index) => (
          <WaypointFormRow
            key={wp.localId}
            index={index}
            value={wp}
            canRemove={waypoints.length > 2}
            onChange={(next) => updateWaypoint(wp.localId, next)}
            onRemove={() => removeWaypoint(wp.localId)}
          />
        ))}
      </section>

      {formError && (
        <p className="text-sm text-rose-400 bg-rose-500/10 rounded-xl px-3 py-2">{formError}</p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="w-full flex items-center justify-center gap-2 rounded-2xl py-3.5 font-semibold text-slate-950 bg-gradient-to-r from-cyan-400 to-emerald-400 disabled:opacity-60"
      >
        {submitting ? (
          <>
            <Loader2 size={18} className="animate-spin" />
            Yuborilmoqda...
          </>
        ) : (
          <>
            <Send size={18} />
            Buyurtma yaratish
          </>
        )}
      </button>
    </form>
  );
};
