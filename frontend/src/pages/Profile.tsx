import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { apiRequest } from "../api";
import {
  Shield,
  KeyRound,
  Trash2,
  Lock,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";

export const Profile: React.FC = () => {
  const { user, updateProfile, logout } = useAuth();
  
  // Profile update state
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [language, setLanguage] = useState(user?.language || "uz");
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState("");
  const [profileError, setProfileError] = useState("");

  // Password update state
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSavingPassword, setIsSavingPassword] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [passwordError, setPasswordError] = useState("");

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingProfile(true);
    setProfileSuccess("");
    setProfileError("");

    try {
      await updateProfile({
        full_name: fullName,
        language: language,
      });
      setProfileSuccess("Profil muvaffaqiyatli yangilandi.");
    } catch (err: any) {
      setProfileError(err.message || "Profilni yangilashda xatolik.");
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingPassword(true);
    setPasswordSuccess("");
    setPasswordError("");

    if (newPassword !== confirmPassword) {
      setPasswordError("Yangi parollar bir-biriga mos kelmadi.");
      setIsSavingPassword(false);
      return;
    }

    if (newPassword.length < 8) {
      setPasswordError("Yangi parol kamida 8 ta belgidan iborat bo'lishi kerak.");
      setIsSavingPassword(false);
      return;
    }

    try {
      await apiRequest("/auth/me/password", {
        method: "PATCH",
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword,
        }),
      });
      setPasswordSuccess("Parol muvaffaqiyatli o'zgartirildi!");
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err: any) {
      setPasswordError(err.message || "Parolni o'zgartirishda xatolik.");
    } finally {
      setIsSavingPassword(false);
    }
  };

  const handleDeactivateAccount = async () => {
    const confirmation = window.confirm(
      "DIQQAT! Akkauntingizni deaktivatsiya qilmoqchimisiz? Ushbu amal bajarilgandan so'ng siz tizimga kira olmaysiz!"
    );
    if (!confirmation) return;

    try {
      await apiRequest("/auth/me", {
        method: "DELETE",
      });
      alert("Akkaunt muvaffaqiyatli deaktivatsiya qilindi. Tizimdan chiqilmoqda.");
      await logout();
      window.location.href = "/login";
    } catch (err: any) {
      alert(err.message || "Akkauntni o'chirishda xatolik.");
    }
  };

  return (
    <div className="profile-page">
      <div className="profile-grid">
        {/* EDIT PROFILE DETAILS */}
        <div className="profile-card glass-card">
          <div className="card-header-row">
            <Shield size={18} className="icon-blue" />
            <h4>Profil Tafsilotlari</h4>
          </div>

          {profileSuccess && <div className="alert-message success-alert"><CheckCircle size={14} /> {profileSuccess}</div>}
          {profileError && <div className="alert-message danger-alert"><AlertTriangle size={14} /> {profileError}</div>}

          <form onSubmit={handleUpdateProfile} className="profile-form">
            <div className="form-group">
              <label>Telegram ID:</label>
              <input type="text" className="glass-input" value={user?.id || ""} disabled />
              <span className="helper-text">Sizning Telegram hisobingiz kodi (ID) o'zgartirilmaydi.</span>
            </div>

            <div className="form-group">
              <label>Telegram Username:</label>
              <input type="text" className="glass-input" value={user?.username ? `@${user.username}` : "Username o'rnatilmagan"} disabled />
            </div>

            <div className="form-group">
              <label>To'liq Ism (F.I.SH):</label>
              <input
                type="text"
                className="glass-input"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>Afzal ko'rilgan Til:</label>
              <select
                className="glass-select"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
              >
                <option value="uz">O'zbekcha (Lotin)</option>
                <option value="uz_cyrl">Ўзбекча (Кирилл)</option>
                <option value="ru">Русский</option>
              </select>
            </div>

            <button type="submit" className="btn btn-primary" disabled={isSavingProfile}>
              {isSavingProfile ? "Saqlanmoqda..." : "Profilni Yangilash"}
            </button>
          </form>
        </div>

        {/* CHANGE PASSWORD */}
        <div className="profile-card glass-card">
          <div className="card-header-row">
            <KeyRound size={18} className="icon-orange" />
            <h4>Parolni O'zgartirish</h4>
          </div>

          {passwordSuccess && <div className="alert-message success-alert"><CheckCircle size={14} /> {passwordSuccess}</div>}
          {passwordError && <div className="alert-message danger-alert"><AlertTriangle size={14} /> {passwordError}</div>}

          <form onSubmit={handleChangePassword} className="profile-form">
            <div className="form-group">
              <label>Amaldagi Parol:</label>
              <div className="password-input-field">
                <Lock size={16} className="field-icon" />
                <input
                  type="password"
                  className="glass-input"
                  placeholder="Eski parolni kiriting"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label>Yangi Parol:</label>
              <div className="password-input-field">
                <Lock size={16} className="field-icon" />
                <input
                  type="password"
                  className="glass-input"
                  placeholder="Kamida 8 ta belgi"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label>Yangi Parolni Tasdiqlang:</label>
              <div className="password-input-field">
                <Lock size={16} className="field-icon" />
                <input
                  type="password"
                  className="glass-input"
                  placeholder="Yangi parolni qayta kiriting"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                />
              </div>
            </div>

            <button type="submit" className="btn btn-primary" disabled={isSavingPassword}>
              {isSavingPassword ? "O'zgartirilmoqda..." : "Parolni Yangilash"}
            </button>
          </form>
        </div>
      </div>

      {/* ACCOUNT DEACTIVATION CAUTION SECTION */}
      <div className="deactivate-card glass-card">
        <div className="deactivate-content">
          <div className="caution-header">
            <AlertTriangle size={24} className="icon-danger animate-pulse-danger" />
            <div>
              <h4>Havfli Zona (Xavfsizlik)</h4>
              <p>Akkauntingizni deaktivatsiya qilish. Ushbu amal orqali tizimga qayta kira olmaysiz.</p>
            </div>
          </div>
          <button className="btn btn-danger" onClick={handleDeactivateAccount}>
            <Trash2 size={16} /> Akkauntni Deaktivatsiya Qilish
          </button>
        </div>
      </div>

      <style>{`
        .profile-page {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .profile-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }

        @media (max-width: 900px) {
          .profile-grid {
            grid-template-columns: 1fr;
          }
        }

        .profile-card {
          padding: 24px;
        }

        .card-header-row {
          display: flex;
          align-items: center;
          gap: 10px;
          border-bottom: 1px solid var(--border-color);
          padding-bottom: 16px;
          margin-bottom: 20px;
        }

        .card-header-row h4 {
          font-size: 15px;
          font-weight: 700;
        }

        .icon-blue { color: var(--accent-secondary); }
        .icon-orange { color: var(--warning); }
        .icon-danger { color: var(--danger); }

        .profile-form {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .password-input-field {
          position: relative;
          display: flex;
          align-items: center;
        }

        .password-input-field .field-icon {
          position: absolute;
          left: 14px;
          color: var(--text-muted);
        }

        .password-input-field .glass-input {
          padding-left: 40px;
        }

        /* Danger area */
        .deactivate-card {
          border-color: rgba(255, 23, 68, 0.2);
          padding: 24px;
          background: rgba(255, 23, 68, 0.02);
        }

        .deactivate-content {
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 20px;
        }

        .caution-header {
          display: flex;
          align-items: center;
          gap: 16px;
        }

        .caution-header h4 {
          font-size: 14px;
          font-weight: 700;
          color: #ff8a80;
        }

        .caution-header p {
          font-size: 13px;
          color: var(--text-secondary);
        }

        .animate-pulse-danger {
          animation: pulse-danger 2s infinite ease-in-out;
        }

        @keyframes pulse-danger {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.6; transform: scale(0.95); }
        }
      `}</style>
    </div>
  );
};
