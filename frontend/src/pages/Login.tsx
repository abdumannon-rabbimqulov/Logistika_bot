import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { KeyRound, Phone, ShieldCheck, Lock, ArrowRight, CornerDownLeft, Eye, EyeOff } from "lucide-react";
import { formatPhoneForApi } from "../utils/phone";
import { initTelegramWebApp, isTelegramWebApp } from "../auth/telegram";

export const Login: React.FC = () => {
  const {
    login,
    loginWithTelegram,
    resetPhone,
    verifyResetCode,
    resetPassword,
    isTelegramApp,
  } = useAuth();
  const navigate = useNavigate();
  const telegramLoginAttempted = useRef(false);

  const [phoneNumber, setPhoneNumber] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const [isForgotMode, setIsForgotMode] = useState(false);
  const [forgotStep, setForgotStep] = useState(1);
  const [resetCode, setResetCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phoneNumber.trim() || !password) {
      setError("Telefon raqami va parolni kiriting.");
      return;
    }

    setError("");
    setIsLoading(true);

    try {
      const result = await login(formatPhoneForApi(phoneNumber.trim()), password);
      navigate(result.redirectTo, { replace: true });
    } catch (err: any) {
      setError(err.message || "Tizimga kirishda xatolik yuz berdi.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccessMsg("");
    setIsLoading(true);

    try {
      if (forgotStep === 1) {
        await resetPhone(formatPhoneForApi(phoneNumber.trim()));
        setSuccessMsg("Tasdiqlash kodi Telegram bot orqali yuborildi!");
        setForgotStep(2);
      } else if (forgotStep === 2) {
        await verifyResetCode(resetCode);
        setSuccessMsg("Kod muvaffaqiyatli tasdiqlandi!");
        setForgotStep(3);
      } else if (forgotStep === 3) {
        if (newPassword.length < 8) {
          throw new Error("Parol kamida 8 ta belgidan iborat bo'lishi kerak.");
        }
        await resetPassword(newPassword, confirmPassword);
        setSuccessMsg("Parol muvaffaqiyatli tiklandi! Yangi parolingiz bilan tizimga kiring.");
        setIsForgotMode(false);
        setForgotStep(1);
        setPassword("");
      }
    } catch (err: any) {
      setError(err.message || "Amalni bajarishda xatolik.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!isTelegramWebApp() || telegramLoginAttempted.current) return;
    telegramLoginAttempted.current = true;
    initTelegramWebApp();

    loginWithTelegram()
      .then((result) => {
        if (result) {
          navigate(result.redirectTo, { replace: true });
        }
      })
      .catch((err: Error) => {
        setError(err.message || "Telegram orqali kirishda xatolik.");
        telegramLoginAttempted.current = false;
      });
  }, [loginWithTelegram, navigate]);

  return (
    <div className="login-page">
      <div className="background-decor">
        <div className="glow glow-1"></div>
        <div className="glow glow-2"></div>
      </div>

      <div className="login-container">
        <div className="login-card glass-card">
          <div className="login-header">
            <div className="logo-badge">
              <ShieldCheck size={32} />
            </div>
            <h2>Logistika AI</h2>
            <p>
              {isTelegramApp
                ? "Telegram orqali avtomatik kirish..."
                : "Tizimga kirish yoki parolni tiklash"}
            </p>
          </div>

          {error && <div className="alert-message danger-alert">{error}</div>}
          {successMsg && <div className="alert-message success-alert">{successMsg}</div>}

          {!isForgotMode ? (
            <form onSubmit={handleLoginSubmit} className="login-form">
              <div className="input-wrapper">
                <label>Telefon raqam</label>
                <div className="input-field">
                  <Phone size={18} className="field-icon" />
                  <input
                    type="tel"
                    placeholder="90 123 45 67 yoki xalqaro raqam"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value.replace(/[^0-9+]/g, ""))}
                    className="glass-input"
                    disabled={isLoading}
                  />
                </div>
              </div>

              <div className="input-wrapper">
                <div className="label-row">
                  <label>Parol</label>
                  <button
                    type="button"
                    className="forgot-link"
                    onClick={() => {
                      setIsForgotMode(true);
                      setForgotStep(1);
                      setError("");
                      setSuccessMsg("");
                    }}
                  >
                    Parolni unutdingizmi?
                  </button>
                </div>
                <div className="input-field">
                  <Lock size={18} className="field-icon" />
                  <input
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="glass-input"
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button type="submit" className="btn btn-primary login-btn" disabled={isLoading}>
                {isLoading ? "Kirilmoqda..." : "Kirish"} <ArrowRight size={18} />
              </button>
            </form>
          ) : (
            <form onSubmit={handleForgotSubmit} className="login-form">
              {forgotStep === 1 && (
                <div className="input-wrapper">
                  <label>Telefon raqamingiz</label>
                  <div className="input-field">
                    <Phone size={18} className="field-icon" />
                    <input
                      type="tel"
                      placeholder="90 123 45 67 yoki xalqaro raqam"
                      value={phoneNumber}
                      onChange={(e) => setPhoneNumber(e.target.value.replace(/[^0-9+]/g, ""))}
                      className="glass-input"
                      disabled={isLoading}
                    />
                  </div>
                  <span className="helper-text">
                    Ushbu raqamga bog'langan Telegram hisobingizga tasdiqlash kodi yuboriladi.
                  </span>
                </div>
              )}

              {forgotStep === 2 && (
                <div className="input-wrapper">
                  <label>Tasdiqlash kodi (Telegram botdan olingan)</label>
                  <div className="input-field">
                    <KeyRound size={18} className="field-icon" />
                    <input
                      type="text"
                      placeholder="Kodni kiriting"
                      value={resetCode}
                      onChange={(e) => setResetCode(e.target.value)}
                      className="glass-input"
                      disabled={isLoading}
                    />
                  </div>
                </div>
              )}

              {forgotStep === 3 && (
                <>
                  <div className="input-wrapper">
                    <label>Yangi parol</label>
                    <div className="input-field">
                      <Lock size={18} className="field-icon" />
                      <input
                        type="password"
                        placeholder="Yangi parol (kamida 8 ta belgi)"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        className="glass-input"
                        disabled={isLoading}
                      />
                    </div>
                  </div>

                  <div className="input-wrapper">
                    <label>Yangi parolni tasdiqlang</label>
                    <div className="input-field">
                      <Lock size={18} className="field-icon" />
                      <input
                        type="password"
                        placeholder="Parolni qayta kiriting"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        className="glass-input"
                        disabled={isLoading}
                      />
                    </div>
                  </div>
                </>
              )}

              <button type="submit" className="btn btn-primary login-btn" disabled={isLoading}>
                {isLoading
                  ? "Yuklanmoqda..."
                  : forgotStep === 1
                    ? "Kod yuborish"
                    : forgotStep === 2
                      ? "Kodni tasdiqlash"
                      : "Parolni yangilash"}
                <ArrowRight size={18} />
              </button>

              <button
                type="button"
                className="btn btn-secondary back-btn"
                onClick={() => {
                  setIsForgotMode(false);
                  setForgotStep(1);
                  setError("");
                  setSuccessMsg("");
                }}
                disabled={isLoading}
              >
                <CornerDownLeft size={16} /> Login sahifasiga qaytish
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};
