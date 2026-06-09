import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  MapPin,
  Star,
  Truck,
  Wallet,
  LogOut,
} from "lucide-react";
import {
  fetchDriverMe,
  fetchTruckTypes,
  updateDriverMe,
} from "../../services/driverApi";
import { useToast } from "../../components/ui/Toast";
import { Skeleton } from "../../components/ui/Skeleton";
import type { DriverProfile } from "../../types/driver";
import type { TruckType } from "../../types/auth";
import { useAuth } from "../../context/AuthContext";



export const DriverProfilePage: React.FC = () => {
  const { toast } = useToast();
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<DriverProfile | null>(null);
  const [truckTypes, setTruckTypes] = useState<TruckType[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const [truckNumber, setTruckNumber] = useState("");
  const [truckYear, setTruckYear] = useState("");
  const [truckTypeId, setTruckTypeId] = useState("");
  const [currentCity, setCurrentCity] = useState("");
  const [currentRegion, setCurrentRegion] = useState("");

  const handleLogout = async () => {
    try {
      await logout();
      navigate("/login", { replace: true });
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Chiqishda xatolik yuz berdi", "error");
    }
  };

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
      setShowForm(false);
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Xatolik", "error");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full rounded-2xl" />
        <Skeleton className="h-20 w-full rounded-2xl" />
        <Skeleton className="h-20 w-full rounded-2xl" />
      </div>
    );
  }

  if (!profile) {
    return <p className="text-center text-slate-400 py-12">Profil topilmadi</p>;
  }

  const isLive = profile.user_status === "LIVE";

  return (
    <div className="space-y-4 pb-8">
      <div className="rounded-2xl border border-white/5 bg-slate-800/60 backdrop-blur-md p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-xl font-bold text-white">{profile.name}</h2>
            <p className="text-xs text-slate-500 mt-1">{profile.phone_number || "—"}</p>
          </div>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-bold ${isLive
                ? "bg-emerald-500/15 text-emerald-300"
                : "bg-slate-700 text-slate-400"
              }`}
          >
            <span
              className={`h-1.5 w-1.5 rounded-full ${isLive ? "bg-emerald-400" : "bg-slate-500"}`}
            />
            {profile.user_status}
          </span>
        </div>
        <div className="mt-4 flex items-center gap-2">
          <Star size={18} className="text-amber-400" fill="currentColor" />
          <span className="text-lg font-bold text-white">
            {Number(profile.rating).toFixed(1)}
          </span>
          <span className="text-sm text-slate-500">· {profile.total_trips} safar</span>
        </div>
      </div>

      <div className="rounded-2xl border border-white/5 bg-gradient-to-br from-emerald-900/30 to-slate-800/60 p-5">
        <div className="flex items-center gap-2 text-slate-400 text-xs uppercase tracking-wider mb-1">
          <Wallet size={14} />
          Balans
        </div>
        <p className="text-2xl font-bold text-white">{profile.balance}</p>
        <p className="text-xs text-slate-500 mt-1">
          GPS: {profile.gps_status} · {profile.truck_type_name || "Mashina"}
        </p>
      </div>



      <button
        type="button"
        onClick={() => setShowForm((v) => !v)}
        className="w-full flex items-center justify-center gap-2 rounded-2xl border border-white/10 bg-slate-800/50 py-3 text-sm font-semibold text-slate-300"
      >
        <Truck size={18} />
        {showForm ? "Mashina sozlamalarini yashirish" : "Mashina sozlamalari"}
      </button>

      {showForm && (
        <form
          onSubmit={handleSave}
          className="space-y-4 rounded-2xl border border-white/5 bg-slate-800/50 p-5"
        >
          {[
            { label: "Mashina raqami", value: truckNumber, set: setTruckNumber, type: "text" },
            { label: "Yil", value: truckYear, set: setTruckYear, type: "number" },
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
            className="w-full rounded-2xl bg-white text-slate-900 py-3.5 font-bold disabled:opacity-50"
          >
            {saving ? "Saqlanmoqda..." : "Saqlash"}
          </button>
        </form>
      )}

      <button
        type="button"
        className="w-full flex items-center justify-center gap-2 rounded-2xl bg-slate-800/80 hover:bg-slate-700 border border-white/5 py-3.5 text-sm font-bold text-slate-300 transition active:scale-[0.99] mt-6"
        onClick={handleLogout}
      >
        <LogOut size={18} /> Chiqish
      </button>
    </div>
  );
};
