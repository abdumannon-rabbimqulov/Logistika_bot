import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { KeyRound, Phone, ShieldCheck, Lock, ArrowRight, CornerDownLeft, Eye, EyeOff } from "lucide-react";
import { formatPhoneForApi } from "../utils/phone";

export const Login: React.FC = () => {
  const { login, resetPhone, verifyResetCode, resetPassword, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // Redirect if already logged in
  useEffect(() => {
    if (isAuthenticated) {
      const from = (location.state as any)?.from?.pathname || "/dashboard";
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  // Form states
  const [phoneNumber, setPhoneNumber] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Forgot password flow states
  const [isForgotMode, setIsForgotMode] = useState(false);
  const [forgotStep, setForgotStep] = useState(1); // 1: phone, 2: code, 3: new password
  const [resetCode, setResetCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  // Handle standard login submit
  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!phoneNumber || !password) {
      setError("Telefon raqami va parolni kiriting.");
      return;
    }

    setError("");
    setIsLoading(true);

    try {
      await login(formatPhoneForApi(phoneNumber), password);
      navigate("/dashboard");
    } catch (err: any) {
      setError(err.message || "Tizimga kirishda xatolik yuz berdi.");
    } finally {
      setIsLoading(false);
    }
  };

  // Handle forgot password stages
  const handleForgotSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccessMsg("");
    setIsLoading(true);

    try {
      if (forgotStep === 1) {
        await resetPhone(formatPhoneForApi(phoneNumber));
        setSuccessMsg("Tasdiqlash kodi Telegram bot orqali yuborildi!");
        setForgotStep(2);
      } else if (forgotStep === 2) {
        // Step 2: Verify Code
        await verifyResetCode(resetCode);
        setSuccessMsg("Kod muvaffaqiyatli tasdiqlandi!");
        setForgotStep(3);
      } else if (forgotStep === 3) {
        // Step 3: Save new password
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
            <p>Tizimga kirish yoki parolni tiklash</p>
          </div>

          {error && <div className="alert-message danger-alert">{error}</div>}
          {successMsg && <div className="alert-message success-alert">{successMsg}</div>}

          {!isForgotMode ? (
            /* STANDARD LOGIN FORM */
            <form onSubmit={handleLoginSubmit} className="login-form">
              <div className="input-wrapper">
                <label>Telefon raqam</label>
                <div className="input-field">
                  <Phone size={18} className="field-icon" />
                  <input
                    type="tel"
                    placeholder="998901234567"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
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
            /* FORGOT / RESET PASSWORD FORM */
            <form onSubmit={handleForgotSubmit} className="login-form">
              {forgotStep === 1 && (
                <div className="input-wrapper">
                  <label>Telefon raqamingiz</label>
                  <div className="input-field">
                    <Phone size={18} className="field-icon" />
                    <input
                      type="tel"
                      placeholder="998901234567"
                      value={phoneNumber}
                      onChange={(e) => setPhoneNumber(e.target.value)}
                      className="glass-input"
                      disabled={isLoading}
                    />
                  </div>
                  <span className="helper-text">Ushbu raqamga bog'langan Telegram hisobingizga tasdiqlash kodi yuboriladi.</span>
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
                {isLoading ? "Yuklanmoqda..." : forgotStep === 1 ? "Kod yuborish" : forgotStep === 2 ? "Kodni tasdiqlash" : "Parolni yangilash"}
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

      <style>{`
        .login-page {
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #06070a;
          position: relative;
          overflow: hidden;
          padding: 20px;
        }

        .background-decor {
          position: absolute;
          width: 100%;
          height: 100%;
          top: 0;
          left: 0;
          z-index: 1;
        }

        .glow {
          position: absolute;
          width: 400px;
          height: 400px;
          border-radius: 50%;
          filter: blur(100px);
          opacity: 0.15;
        }

        .glow-1 {
          background: var(--accent-primary);
          top: -100px;
          left: -100px;
          animation: floatGlow 12s infinite ease-in-out alternate;
        }

        .glow-2 {
          background: var(--accent-secondary);
          bottom: -100px;
          right: -100px;
          animation: floatGlow 15s infinite ease-in-out alternate-reverse;
        }

        @keyframes floatGlow {
          0% { transform: translate(0, 0) scale(1); }
          100% { transform: translate(40px, 40px) scale(1.1); }
        }

        .login-container {
          position: relative;
          z-index: 2;
          width: 100%;
          max-width: 440px;
        }

        .login-card {
          padding: 40px 32px;
          border-radius: var(--border-radius-lg);
          display: flex;
          flex-direction: column;
          gap: 24px;
        }

        .login-header {
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
        }

        .logo-badge {
          width: 60px;
          height: 60px;
          border-radius: 16px;
          background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          box-shadow: 0 8px 24px rgba(88, 101, 242, 0.4);
          margin-bottom: 12px;
        }

        .login-header h2 {
          font-size: 24px;
          font-weight: 800;
          letter-spacing: -0.03em;
        }

        .login-header p {
          font-size: 13px;
          color: var(--text-secondary);
        }

        .alert-message {
          padding: 12px 16px;
          border-radius: var(--border-radius);
          font-size: 13px;
          font-weight: 500;
          animation: shake 0.3s cubic-bezier(.36,.07,.19,.97) both;
        }

        @keyframes shake {
          10%, 90% { transform: translate3d(-1px, 0, 0); }
          20%, 80% { transform: translate3d(2px, 0, 0); }
          30%, 50%, 70% { transform: translate3d(-4px, 0, 0); }
          40%, 60% { transform: translate3d(4px, 0, 0); }
        }

        .danger-alert {
          background: rgba(255, 23, 68, 0.1);
          border: 1px solid rgba(255, 23, 68, 0.25);
          color: #ff8a80;
        }

        .success-alert {
          background: rgba(0, 230, 118, 0.1);
          border: 1px solid rgba(0, 230, 118, 0.25);
          color: #b9f6ca;
        }

        .login-form {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .input-wrapper {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .label-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .input-wrapper label {
          font-size: 13px;
          font-weight: 600;
          color: var(--text-secondary);
        }

        .forgot-link {
          background: none;
          border: none;
          color: var(--accent-secondary);
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          transition: color 0.2s;
        }

        .forgot-link:hover {
          color: var(--accent-secondary-hover);
        }

        .input-field {
          position: relative;
          display: flex;
          align-items: center;
        }

        .field-icon {
          position: absolute;
          left: 14px;
          color: var(--text-muted);
          pointer-events: none;
        }

        .input-field .glass-input {
          padding-left: 44px;
        }

        .password-toggle {
          position: absolute;
          right: 14px;
          background: none;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          display: flex;
          align-items: center;
          transition: color 0.2s;
        }

        .password-toggle:hover {
          color: var(--text-primary);
        }

        .helper-text {
          font-size: 11px;
          color: var(--text-muted);
          margin-top: 4px;
        }

        .login-btn {
          width: 100%;
          justify-content: center;
          padding: 14px;
          font-size: 15px;
          margin-top: 8px;
        }

        .back-btn {
          width: 100%;
          justify-content: center;
          padding: 12px;
          font-size: 13px;
          margin-top: 4px;
        }
      `}</style>
    </div>
  );
};
