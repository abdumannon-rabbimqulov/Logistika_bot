import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Truck, ArrowLeft } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { createDriverProfile, fetchTruckTypes } from "../services/driverApi";
import type { TruckType } from "../types/auth";
import { formatPhoneForApi } from "../utils/phone";

export const DriverSetupProfile: React.FC = () => {
  const navigate = useNavigate();
  const { session, completeDriverProfile, refreshMe } = useAuth();

  const [truckTypes, setTruckTypes] = useState<TruckType[]>([]);
  const [loadingTypes, setLoadingTypes] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const [currentCity, setCurrentCity] = useState("");
  const [currentRegion, setCurrentRegion] = useState("");
  const [phoneNumber, setPhoneNumber] = useState("");
  const [truckNumber, setTruckNumber] = useState("");
  const [truckTypeId, setTruckTypeId] = useState("");
  const [truckYear, setTruckYear] = useState("");

  useEffect(() => {
    fetchTruckTypes()
      .then((items) => {
        setTruckTypes(items);
        if (items.length > 0) setTruckTypeId(String(items[0].id));
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoadingTypes(false));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!currentCity.trim() || !truckNumber.trim() || !truckTypeId) {
      setError("Majburiy maydonlarni to'ldiring");
      return;
    }
    setSubmitting(true);
    try {
      await createDriverProfile({
        current_city: currentCity.trim(),
        current_region: currentRegion.trim() || undefined,
        phone_number: phoneNumber.trim() ? formatPhoneForApi(phoneNumber.trim()) : undefined,
        truck_number: truckNumber.trim(),
        truck_type_id: Number(truckTypeId),
        truck_year: truckYear ? Number(truckYear) : undefined,
      });
      completeDriverProfile();
      await refreshMe();
      navigate("/driver", { replace: true });
    } catch (ex: unknown) {
      setError(ex instanceof Error ? ex.message : "Saqlanmadi");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mobile-app-root">
      <div className="mobile-phone">
        <header className="mobile-header">
          <button type="button" className="back-btn" onClick={() => navigate("/login")}>
            <ArrowLeft size={20} />
          </button>
          <h1>Haydovchi profili</h1>
        </header>

        <div className="mobile-content no-nav p-4 pb-8 space-y-4">
          {session?.message && (
            <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-400">
              {session.message}
            </div>
          )}
          {error && (
            <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-400">
              {error}
            </div>
          )}

          <div className="rounded-2xl border border-white/5 bg-slate-800/60 backdrop-blur-md p-5 shadow-lg">
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div>
                <label className="mb-1.5 block text-xs font-semibold text-slate-400">Hozirgi shahar *</label>
                <input
                  className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white text-base focus:border-cyan-500 focus:outline-none transition"
                  value={currentCity}
                  onChange={(e) => setCurrentCity(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold text-slate-400">Viloyat</label>
                <input
                  className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white text-base focus:border-cyan-500 focus:outline-none transition"
                  value={currentRegion}
                  onChange={(e) => setCurrentRegion(e.target.value)}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold text-slate-400">Telefon</label>
                <input
                  className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white text-base focus:border-cyan-500 focus:outline-none transition"
                  type="tel"
                  placeholder="90 123 45 67 yoki xalqaro raqam"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value.replace(/[^0-9+]/g, ""))}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold text-slate-400">Mashina raqami *</label>
                <input
                  className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white text-base focus:border-cyan-500 focus:outline-none transition"
                  value={truckNumber}
                  onChange={(e) => setTruckNumber(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold text-slate-400">Mashina turi *</label>
                <select
                  className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white text-base focus:border-cyan-500 focus:outline-none transition"
                  value={truckTypeId}
                  onChange={(e) => setTruckTypeId(e.target.value)}
                  disabled={loadingTypes}
                  required
                >
                  {truckTypes.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-semibold text-slate-400">Ishlab chiqarilgan yil</label>
                <input
                  className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white text-base focus:border-cyan-500 focus:outline-none transition"
                  type="number"
                  min={1980}
                  max={2030}
                  value={truckYear}
                  onChange={(e) => setTruckYear(e.target.value)}
                />
              </div>
              <button
                type="submit"
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 py-3.5 text-sm font-bold text-white disabled:opacity-50 transition active:scale-[0.99] mt-2"
                disabled={submitting}
              >
                <Truck size={18} />
                {submitting ? "Saqlanmoqda..." : "Profilni saqlash"}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
