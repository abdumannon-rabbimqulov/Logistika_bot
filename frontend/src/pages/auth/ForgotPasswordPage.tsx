import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";
import { formatPhoneForApi } from "../../utils/phone";
import { ArrowLeft, KeyRound, Lock, Phone, ShieldCheck, ArrowRight } from "lucide-react";

export const ForgotPasswordPage: React.FC = () => {
  const { resetPhone, verifyResetCode, resetPassword } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      if (step === 1) {
        await resetPhone(formatPhoneForApi(phone.trim()));
        setSuccess("Kod Telegram bot orqali yuborildi");
        setStep(2);
      } else if (step === 2) {
        await verifyResetCode(code);
        setSuccess("Kod tasdiqlandi");
        setStep(3);
      } else {
        if (newPassword.length < 8) throw new Error("Parol kamida 8 belgi");
        await resetPassword(newPassword, confirmPassword);
        setSuccess("Parol tiklandi. Endi kiring.");
        setTimeout(() => navigate("/login", { replace: true }), 1500);
      }
    } catch (ex: unknown) {
      setError(ex instanceof Error ? ex.message : "Xatolik");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="background-decor">
        <div className="glow glow-1" />
        <div className="glow glow-2" />
      </div>

      <div className="login-container">
        <div className="login-card glass-card">
          <div className="login-header">
            <button
              type="button"
              className="forgot-link"
              style={{ alignSelf: "flex-start", marginBottom: 4 }}
              onClick={() => navigate("/login")}
            >
              <ArrowLeft size={16} style={{ marginRight: 6 }} />
              Orqaga
            </button>
            <div className="logo-badge">
              <ShieldCheck size={32} />
            </div>
            <h2>Parolni tiklash</h2>
            <p>
              {step === 1 && "Telefon raqamingizni kiriting"}
              {step === 2 && "Telegram botdan kelgan kodni kiriting"}
              {step === 3 && "Yangi parol o'rnating"}
            </p>
            <div className="mobile-step-dots" style={{ marginTop: 12 }}>
              {[1, 2, 3].map((s) => (
                <span key={s} className={`mobile-step-dot${step === s ? " active" : ""}`} />
              ))}
            </div>
          </div>

          {error && <div className="alert-message danger-alert">{error}</div>}
          {success && <div className="alert-message success-alert">{success}</div>}

          <form className="login-form" onSubmit={handleSubmit}>
            {step === 1 && (
              <div className="input-wrapper">
                <label>Telefon raqam</label>
                <div className="input-field">
                  <Phone size={18} className="field-icon" />
                  <input
                    type="tel"
                    className="glass-input"
                    placeholder="998901234567"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value.replace(/[^0-9+]/g, ""))}
                    disabled={loading}
                    required
                  />
                </div>
              </div>
            )}
            {step === 2 && (
              <div className="input-wrapper">
                <label>Tasdiqlash kodi</label>
                <div className="input-field">
                  <KeyRound size={18} className="field-icon" />
                  <input
                    type="text"
                    className="glass-input"
                    placeholder="Kodni kiriting"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    disabled={loading}
                    required
                  />
                </div>
              </div>
            )}
            {step === 3 && (
              <>
                <div className="input-wrapper">
                  <label>Yangi parol</label>
                  <div className="input-field">
                    <Lock size={18} className="field-icon" />
                    <input
                      type="password"
                      className="glass-input"
                      placeholder="Kamida 8 belgi"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      disabled={loading}
                      required
                    />
                  </div>
                </div>
                <div className="input-wrapper">
                  <label>Parolni tasdiqlang</label>
                  <div className="input-field">
                    <Lock size={18} className="field-icon" />
                    <input
                      type="password"
                      className="glass-input"
                      placeholder="Qayta kiriting"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      disabled={loading}
                      required
                    />
                  </div>
                </div>
              </>
            )}

            <button type="submit" className="btn btn-primary login-btn" disabled={loading}>
              {loading ? "Yuklanmoqda..." : step === 3 ? "Parolni saqlash" : "Davom etish"}
              <ArrowRight size={18} />
            </button>
          </form>

          <p style={{ textAlign: "center", fontSize: 14 }}>
            <Link to="/login" style={{ color: "var(--accent-secondary)" }}>
              Login sahifasiga
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};
