import React, { useEffect, useState } from "react";
import {
  fetchDriverMe,
  fetchTruckTypes,
  updateDriverMe,
} from "../../services/driverApi";
import { useLocation } from "../../context/LocationContext";
import { useToast } from "../../components/ui/Toast";
import { Skeleton } from "../../components/ui/Skeleton";
import type { DriverProfile } from "../../types/driver";
import type { TruckType } from "../../types/auth";
import { MapPin, Radio, Star, Truck } from "lucide-react";

export const DriverProfilePage: React.FC = () => {
  const { toast } = useToast();
  const { enabled, active, toggle, error: gpsError } = useLocation();
  const [profile, setProfile] = useState<DriverProfile | null>(null);
  const [truckTypes, setTruckTypes] = useState<TruckType[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [truckNumber, setTruckNumber] = useState("");
  const [truckYear, setTruckYear] = useState("");
  const [truckTypeId, setTruckTypeId] = useState("");
  const [currentCity, setCurrentCity] = useState("");
  const [currentRegion, setCurrentRegion] = useState("");

  useEffect(() => {
    Promise.all([fetchDriverMe(), fetchTruckTypes()])
      .then(([p, types]) => {
        setProfile(p);
        setTruckTypes(types);
        setTruckNumber(p.truck_number);
        setTruckYear(p.truck_year ? String(p.truck_year) : "");
        setTruckTypeId(String(p.truck_type_id));
        setCurrentCity(p.current_city || "");
        setCurrentRegion(p.current_region || "");
      })
      .catch((ex: unknown) => toast(ex instanceof Error ? ex.message : "Yuklanmadi", "error"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await updateDriverMe({
        truck_number: truckNumber,
        truck_year: truckYear ? Number(truckYear) : undefined,
        truck_type_id: Number(truckTypeId),
        current_city: currentCity,
        current_region: currentRegion || undefined,
      });
      setProfile(updated);
      toast("Profil saqlandi", "success");
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Xatolik", "error");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-24 w-full rounded-2xl" />
        <Skeleton className="h-48 w-full rounded-2xl" />
      </div>
    );
  }

  if (!profile) {
    return <p className="text-center text-slate-400 py-12">Profil topilmadi</p>;
  }

  return (
    <div className="space-y-5 pb-6">
      <div className="rounded-2xl border border-white/5 bg-slate-800/50 backdrop-blur-md p-5">
        <div className="flex items-center gap-2 text-amber-400">
          <Star size={22} fill="currentColor" />
          <span className="text-2xl font-bold text-white">{Number(profile.rating).toFixed(1)}</span>
          <span className="text-sm text-slate-400">· {profile.total_trips} safar</span>
        </div>
      </div>

      <div className="rounded-2xl border border-white/5 bg-slate-800/50 backdrop-blur-md p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`flex h-12 w-12 items-center justify-center rounded-2xl ${
                enabled && active ? "bg-emerald-500/20" : "bg-slate-700/80"
              }`}
            >
              <Radio className={enabled && active ? "text-emerald-400 animate-pulse" : "text-slate-400"} size={22} />
            </div>
            <div>
              <p className="font-semibold text-white">Jonli lokatsiya</p>
              <p className="text-xs text-slate-400">
                Global kontekst — sahifa almashganda uzilmaydi
              </p>
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={enabled}
            onClick={toggle}
            className={`relative h-9 w-16 rounded-full transition-colors ${
              enabled ? "bg-emerald-500" : "bg-slate-600"
            }`}
          >
            <span
              className={`absolute top-1 h-7 w-7 rounded-full bg-white shadow transition-all ${
                enabled ? "left-8" : "left-1"
              }`}
            />
          </button>
        </div>
        {gpsError && <p className="text-xs text-rose-400 mt-3">{gpsError}</p>}
      </div>

      <form
        onSubmit={handleSave}
        className="space-y-4 rounded-2xl border border-white/5 bg-slate-800/50 backdrop-blur-md p-5"
      >
        <h3 className="font-bold text-white flex items-center gap-2">
          <Truck size={18} /> Mashina
        </h3>
        {[
          { label: "Mashina raqami", value: truckNumber, set: setTruckNumber, type: "text" },
          { label: "Ishlab chiqarilgan yil", value: truckYear, set: setTruckYear, type: "number" },
        ].map((f) => (
          <div key={f.label}>
            <label className="text-xs text-slate-400">{f.label}</label>
            <input
              type={f.type}
              className="mt-1 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white text-base"
              value={f.value}
              onChange={(e) => f.set(e.target.value)}
            />
          </div>
        ))}
        <div>
          <label className="text-xs text-slate-400">Mashina turi</label>
          <select
            className="mt-1 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white"
            value={truckTypeId}
            onChange={(e) => setTruckTypeId(e.target.value)}
          >
            {truckTypes.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-slate-400 flex items-center gap-1">
            <MapPin size={12} /> Shahar
          </label>
          <input
            className="mt-1 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white"
            value={currentCity}
            onChange={(e) => setCurrentCity(e.target.value)}
            required
          />
        </div>
        <div>
          <label className="text-xs text-slate-400">Viloyat</label>
          <input
            className="mt-1 w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white"
            value={currentRegion}
            onChange={(e) => setCurrentRegion(e.target.value)}
          />
        </div>
        <button
          type="submit"
          disabled={saving}
          className="w-full rounded-2xl bg-white text-slate-900 py-3.5 font-bold disabled:opacity-50 hover:bg-slate-100 transition"
        >
          {saving ? "Saqlanmoqda..." : "Saqlash"}
        </button>
      </form>
    </div>
  );
};
