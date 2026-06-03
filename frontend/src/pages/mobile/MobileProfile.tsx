import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { changePasswordApi, deactivateMeApi } from "../../services/authApi";
import { ConfirmModal } from "../../components/mobile/ConfirmModal";
import { LogOut, Trash2 } from "lucide-react";

export const MobileProfile: React.FC = () => {
  const { user, session, updateProfile, logout, refreshMe } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [language, setLanguage] = useState("uz");
  const [phone, setPhone] = useState("");
  const [bio, setBio] = useState("");
  const [oldPw, setOldPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const [showDelete, setShowDelete] = useState(false);

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || "");
      setLanguage(user.language || "uz");
      setPhone(user.phone_number || "");
      setBio((user as { bio?: string }).bio || "");
    }
  }, [user]);

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr("");
    setMsg("");
    try {
      await updateProfile({
        full_name: fullName,
        language,
        phone_number: phone || undefined,
        bio: bio || undefined,
      } as Parameters<typeof updateProfile>[0]);
      setMsg("Profil saqlandi");
    } catch (ex: unknown) {
      setErr(ex instanceof Error ? ex.message : "Xatolik");
    } finally {
      setBusy(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPw !== confirmPw) {
      setErr("Parollar mos emas");
      return;
    }
    setBusy(true);
    setErr("");
    try {
      await changePasswordApi(oldPw, newPw);
      setMsg("Parol yangilandi");
      setOldPw("");
      setNewPw("");
      setConfirmPw("");
    } catch (ex: unknown) {
      setErr(ex instanceof Error ? ex.message : "Xatolik");
    } finally {
      setBusy(false);
    }
  };

  const handleDeactivate = async () => {
    setBusy(true);
    try {
      await deactivateMeApi();
      await logout();
      navigate("/login", { replace: true });
    } catch (ex: unknown) {
      setErr(ex instanceof Error ? ex.message : "Xatolik");
    } finally {
      setBusy(false);
      setShowDelete(false);
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  if (!user && session?.status !== "need_driver_profile") {
    return (
      <div className="mobile-card">
        <p>Profil yuklanmoqda...</p>
        <button type="button" className="mobile-btn mobile-btn-secondary" onClick={() => refreshMe()}>
          Qayta yuklash
        </button>
      </div>
    );
  }

  return (
    <>
      {msg && <div className="mobile-alert mobile-alert-success">{msg}</div>}
      {err && <div className="mobile-alert mobile-alert-error">{err}</div>}

      <div className="mobile-card">
        <h3>Shaxsiy ma&apos;lumotlar</h3>
        <form className="mobile-form" onSubmit={handleSaveProfile}>
          <div className="mobile-field">
            <label>ID</label>
            <input value={user?.id ?? session?.userId ?? ""} disabled />
          </div>
          <div className="mobile-field">
            <label>To&apos;liq ism</label>
            <input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
          </div>
          <div className="mobile-field">
            <label>Telefon</label>
            <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="998901234567" />
          </div>
          <div className="mobile-field">
            <label>Til</label>
            <select value={language} onChange={(e) => setLanguage(e.target.value)}>
              <option value="uz">O&apos;zbekcha</option>
              <option value="uz_cyrl">Ўзбекча</option>
              <option value="ru">Русский</option>
            </select>
          </div>
          <div className="mobile-field">
            <label>Bio</label>
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              rows={3}
              style={{ minHeight: 80, resize: "vertical" }}
            />
          </div>
          <button type="submit" className="mobile-btn mobile-btn-primary" disabled={busy}>
            Saqlash
          </button>
        </form>
      </div>

      <div className="mobile-card">
        <h3>Parolni o&apos;zgartirish</h3>
        <form className="mobile-form" onSubmit={handleChangePassword}>
          <div className="mobile-field">
            <label>Eski parol</label>
            <input type="password" value={oldPw} onChange={(e) => setOldPw(e.target.value)} required />
          </div>
          <div className="mobile-field">
            <label>Yangi parol</label>
            <input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} required minLength={8} />
          </div>
          <div className="mobile-field">
            <label>Tasdiqlash</label>
            <input type="password" value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)} required />
          </div>
          <button type="submit" className="mobile-btn mobile-btn-secondary" disabled={busy}>
            Parolni yangilash
          </button>
        </form>
      </div>

      <button type="button" className="mobile-btn mobile-btn-secondary" onClick={handleLogout}>
        <LogOut size={18} /> Chiqish
      </button>

      <button
        type="button"
        className="mobile-btn mobile-btn-danger"
        style={{ marginTop: 10 }}
        onClick={() => setShowDelete(true)}
      >
        <Trash2 size={18} /> Akkauntni o&apos;chirish
      </button>

      <ConfirmModal
        open={showDelete}
        title="Akkauntni deaktivatsiya qilish"
        message="Bu amaldan keyin tizimga kira olmaysiz. Davom etasizmi?"
        confirmLabel="Ha, o'chirish"
        danger
        onConfirm={handleDeactivate}
        onCancel={() => setShowDelete(false)}
      />
    </>
  );
};
