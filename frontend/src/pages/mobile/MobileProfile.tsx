import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { changePasswordApi, deactivateMeApi } from "../../services/authApi";
import { ConfirmModal } from "../../components/mobile/ConfirmModal";
import { LogOut, Trash2 } from "lucide-react";
import { formatPhoneForApi } from "../../utils/phone";

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
        full_name: fullName.trim(),
        language,
        phone_number: phone.trim() ? formatPhoneForApi(phone.trim()) : undefined,
        bio: bio.trim() || undefined,
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
      <div className="space-y-4 px-4">
        <div className="rounded-2xl border border-white/5 bg-slate-800/60 backdrop-blur-md p-6 text-center">
          <p className="text-slate-400 mb-4">Profil yuklanmoqda...</p>
          <button
            type="button"
            className="rounded-xl bg-slate-700/50 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-600"
            onClick={() => refreshMe()}
          >
            Qayta yuklash
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-8">
      {msg && (
        <div className="mx-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-400">
          {msg}
        </div>
      )}
      {err && (
        <div className="mx-4 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-400">
          {err}
        </div>
      )}

      <div className="rounded-2xl border border-white/5 bg-slate-800/60 backdrop-blur-md p-5 shadow-lg mx-4">
        <h3 className="mb-4 text-lg font-bold text-white">Shaxsiy ma&apos;lumotlar</h3>
        <form className="space-y-4" onSubmit={handleSaveProfile}>
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-400">ID</label>
            <input
              className="w-full rounded-xl border border-white/10 bg-slate-900/50 px-4 py-3 text-white text-base opacity-50 cursor-not-allowed"
              value={user?.id ?? session?.userId ?? ""}
              disabled
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-400">To&apos;liq ism</label>
            <input
              className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white text-base focus:border-cyan-500 focus:outline-none transition"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-400">Telefon</label>
            <input
              className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white text-base focus:border-cyan-500 focus:outline-none transition"
              value={phone}
              onChange={(e) => setPhone(e.target.value.replace(/[^0-9+]/g, ""))}
              placeholder="90 123 45 67 yoki xalqaro raqam"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-400">Til</label>
            <select
              className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white text-base focus:border-cyan-500 focus:outline-none transition"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option value="uz">O&apos;zbekcha</option>
              <option value="uz_cyrl">Ўзбекча</option>
              <option value="ru">Русский</option>
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-400">Bio</label>
            <textarea
              className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white text-base focus:border-cyan-500 focus:outline-none transition"
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              rows={3}
              style={{ minHeight: 80, resize: "vertical" }}
            />
          </div>
          <button
            type="submit"
            className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 py-3.5 text-sm font-bold text-white disabled:opacity-50 transition active:scale-[0.99] mt-2"
            disabled={busy}
          >
            {busy ? "Saqlanmoqda..." : "Saqlash"}
          </button>
        </form>
      </div>

      <div className="rounded-2xl border border-white/5 bg-slate-800/60 backdrop-blur-md p-5 shadow-lg mx-4 mt-4">
        <h3 className="mb-4 text-lg font-bold text-white">Parolni o&apos;zgartirish</h3>
        <form className="space-y-4" onSubmit={handleChangePassword}>
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-400">Eski parol</label>
            <input
              type="password"
              className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white text-base focus:border-cyan-500 focus:outline-none transition"
              value={oldPw}
              onChange={(e) => setOldPw(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-400">Yangi parol</label>
            <input
              type="password"
              className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white text-base focus:border-cyan-500 focus:outline-none transition"
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              required
              minLength={8}
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-semibold text-slate-400">Tasdiqlash</label>
            <input
              type="password"
              className="w-full rounded-xl border border-white/10 bg-slate-900/80 px-4 py-3 text-white text-base focus:border-cyan-500 focus:outline-none transition"
              value={confirmPw}
              onChange={(e) => setConfirmPw(e.target.value)}
              required
            />
          </div>
          <button
            type="submit"
            className="w-full flex items-center justify-center gap-2 rounded-xl bg-slate-700/50 hover:bg-slate-700 border border-white/10 py-3.5 text-sm font-bold text-white disabled:opacity-50 transition active:scale-[0.99] mt-2"
            disabled={busy}
          >
            {busy ? "Kuting..." : "Parolni yangilash"}
          </button>
        </form>
      </div>

      <div className="px-4 mt-6 space-y-3">
        <button
          type="button"
          className="w-full flex items-center justify-center gap-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 border border-white/5 py-3.5 text-sm font-bold text-slate-300 transition active:scale-[0.99]"
          onClick={handleLogout}
        >
          <LogOut size={18} /> Chiqish
        </button>

        <button
          type="button"
          className="w-full flex items-center justify-center gap-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 py-3.5 text-sm font-bold text-rose-400 transition active:scale-[0.99]"
          onClick={() => setShowDelete(true)}
        >
          <Trash2 size={18} /> Akkauntni o&apos;chirish
        </button>
      </div>

      <ConfirmModal
        open={showDelete}
        title="Akkauntni deaktivatsiya qilish"
        message="Bu amaldan keyin tizimga kira olmaysiz. Davom etasizmi?"
        confirmLabel="Ha, o'chirish"
        danger
        onConfirm={handleDeactivate}
        onCancel={() => setShowDelete(false)}
      />
    </div>
  );
};
