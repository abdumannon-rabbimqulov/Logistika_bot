import { useEffect, useState } from "react";
import { ensureSession, getMyProfile } from "./api/client";
import { hydrateAccessToken } from "./auth/session";

function getTelegramInitData() {
  const tg = window.Telegram?.WebApp;
  if (!tg) {
    throw new Error("Telegram WebApp SDK topilmadi");
  }
  tg.ready();
  tg.expand();
  return tg.initData;
}

export default function App() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function bootstrap() {
      try {
        hydrateAccessToken();
        const initData = getTelegramInitData();
        if (!initData) {
          throw new Error("initData bo'sh");
        }
        await ensureSession(initData);
        const me = await getMyProfile();
        if (mounted) {
          setProfile(me);
        }
      } catch (err) {
        if (mounted) {
          setError(err?.response?.data?.detail || err.message || "Xatolik yuz berdi");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }
    bootstrap();
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) {
    return <main className="card">Yuklanmoqda...</main>;
  }
  if (error) {
    return <main className="card error">Xatolik: {error}</main>;
  }

  return (
    <main className="card">
      <h1>Logistika WebApp</h1>
      <p>
        Salom, <strong>{profile?.full_name}</strong>
      </p>
      <ul>
        <li>Telegram ID: {profile?.id}</li>
        <li>Username: {profile?.username || "-"}</li>
        <li>Telefon: {profile?.phone_number || "-"}</li>
        <li>Til: {profile?.language}</li>
      </ul>
    </main>
  );
}
