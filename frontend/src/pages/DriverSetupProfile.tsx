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
        phone_number: phoneNumber.trim() ? formatPhoneForApi(phoneNumber) : undefined,
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

        <div className="mobile-content no-nav">
          {session?.message && (
            <div className="mobile-alert mobile-alert-success">{session.message}</div>
          )}
          {error && <div className="mobile-alert mobile-alert-error">{error}</div>}

          <form className="mobile-form" onSubmit={handleSubmit}>
            <div className="mobile-field">
              <label>Hozirgi shahar *</label>
              <input value={currentCity} onChange={(e) => setCurrentCity(e.target.value)} required />
            </div>
            <div className="mobile-field">
              <label>Viloyat</label>
              <input value={currentRegion} onChange={(e) => setCurrentRegion(e.target.value)} />
            </div>
            <div className="mobile-field">
              <label>Telefon</label>
              <input
                type="tel"
                placeholder="998901234567"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
              />
            </div>
            <div className="mobile-field">
              <label>Mashina raqami *</label>
              <input value={truckNumber} onChange={(e) => setTruckNumber(e.target.value)} required />
            </div>
            <div className="mobile-field">
              <label>Mashina turi *</label>
              <select
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
            <div className="mobile-field">
              <label>Ishlab chiqarilgan yil</label>
              <input
                type="number"
                min={1980}
                max={2030}
                value={truckYear}
                onChange={(e) => setTruckYear(e.target.value)}
              />
            </div>
            <button type="submit" className="mobile-btn mobile-btn-primary" disabled={submitting}>
              <Truck size={18} />
              {submitting ? "Saqlanmoqda..." : "Profilni saqlash"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
