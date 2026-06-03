import React, { useState } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Sidebar } from "../components/Sidebar";
import { Settings, Server, X, ShieldAlert } from "lucide-react";
import { API_BASE_URL, normalizeApiBaseUrl } from "../api";

export const AdminLayout: React.FC = () => {
  const { isAuthenticated, user, loading } = useAuth();
  const location = useLocation();
  const [showSettings, setShowSettings] = useState(false);
  const [backendUrl, setBackendUrl] = useState(API_BASE_URL);

  if (loading) {
    return (
      <div className="layout-loading">
        <div className="spinner"></div>
        <p>Yuklanmoqda...</p>
        <style>{`
          .layout-loading {
            height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: var(--bg-primary);
            gap: 16px;
            color: var(--text-secondary);
          }
        `}</style>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Double check admin role access
  const isAdmin = user?.role === "admin" || (user && [7915740408, 114631388].includes(user.id));
  if (!isAdmin) {
    return (
      <div className="access-denied">
        <div className="glass-card error-card">
          <ShieldAlert size={48} className="error-icon" />
          <h1>Kirish Taqiqlandi</h1>
          <p>Sizda ushbu sahifaga kirish huquqi yo'q. Loyiha faqat Adminlar uchun ochiq.</p>
          <a href="/login" onClick={() => localStorage.clear()} className="btn btn-primary">Login Sahifasiga Qaytish</a>
        </div>
        <style>{`
          .access-denied {
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--bg-primary);
            padding: 20px;
          }
          .error-card {
            max-width: 500px;
            padding: 40px;
            text-align: center;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px;
          }
          .error-icon {
            color: var(--danger);
          }
        `}</style>
      </div>
    );
  }

  const handleSaveSettings = () => {
    localStorage.setItem("logistika_backend_url", normalizeApiBaseUrl(backendUrl));
    setShowSettings(false);
    window.location.reload();
  };

  const getPageTitle = () => {
    switch (location.pathname) {
      case "/dashboard":
        return "Boshqaruv Paneli Tahlillari";
      case "/orders":
        return "Buyurtmalar Moderatsiyasi";
      case "/users":
        return "Foydalanuvchilar Ro'yxati";
      case "/ai-commands":
        return "AI Buyruqlar Tarixi";
      case "/live-tracking":
        return "Haydovchilarni Xaritada Jonli Kuzatish";
      case "/profile":
        return "Profil Sozlamalari";
      default:
        return "Logistika AI";
    }
  };

  return (
    <div className="admin-layout">
      <Sidebar />
      <div className="main-content">
        <header className="main-header glass-card">
          <div className="header-left">
            <h1>{getPageTitle()}</h1>
          </div>
          <div className="header-right">
            <div className="env-tag badge badge-success">Active API</div>
            <button className="btn btn-secondary btn-icon" onClick={() => setShowSettings(true)}>
              <Settings size={18} />
            </button>
          </div>
        </header>

        <main className="content-viewport">
          <Outlet />
        </main>
      </div>

      {showSettings && (
        <div className="modal-backdrop">
          <div className="glass-card modal-content animate-slide-in">
            <div className="modal-header">
              <h3><Server size={20} /> API Sozlamalari</h3>
              <button className="close-btn" onClick={() => setShowSettings(false)}>
                <X size={18} />
              </button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>FastAPI Backend URL:</label>
                <input
                  type="text"
                  className="glass-input"
                  value={backendUrl}
                  onChange={(e) => setBackendUrl(e.target.value)}
                  placeholder="http://localhost:8000"
                />
                <span className="helper-text">
                  Standart holatda tizim lokal serverga (http://localhost:8000) so'rov yuboradi. Agar API boshqa manzilda bo'lsa, o'zgartiring.
                </span>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowSettings(false)}>
                Bekor qilish
              </button>
              <button className="btn btn-primary" onClick={handleSaveSettings}>
                Saqlash va Yangilash
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .admin-layout {
          display: flex;
          min-height: 100vh;
          background-image: 
            radial-gradient(at 0% 0%, rgba(88, 101, 242, 0.08) 0px, transparent 50%),
            radial-gradient(at 100% 100%, rgba(0, 210, 255, 0.05) 0px, transparent 50%);
          background-color: var(--bg-primary);
        }

        .main-content {
          flex: 1;
          display: flex;
          flex-direction: column;
          padding: 20px 20px 20px 0;
          height: 100vh;
          overflow: hidden;
        }

        .main-header {
          height: var(--header-height);
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 24px;
          border-radius: var(--border-radius-lg);
          margin-bottom: 20px;
          z-index: 5;
        }

        .header-left h1 {
          font-size: 20px;
          font-weight: 700;
          letter-spacing: -0.02em;
        }

        .header-right {
          display: flex;
          align-items: center;
          gap: 16px;
        }

        .env-tag {
          font-size: 11px;
          padding: 6px 12px;
        }

        .content-viewport {
          flex: 1;
          overflow-y: auto;
          padding-right: 4px;
        }

        /* Modal Styles */
        .modal-backdrop {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: rgba(0, 0, 0, 0.6);
          backdrop-filter: blur(8px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 100;
        }

        .modal-content {
          width: 90%;
          max-width: 500px;
          padding: 24px;
          border-radius: var(--border-radius-lg);
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .animate-slide-in {
          animation: slideIn 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        @keyframes slideIn {
          from { transform: translateY(20px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }

        .modal-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-bottom: 1px solid var(--border-color);
          padding-bottom: 16px;
        }

        .modal-header h3 {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 18px;
          color: var(--text-primary);
        }

        .close-btn {
          background: none;
          border: none;
          color: var(--text-secondary);
          cursor: pointer;
          transition: color 0.2s;
        }

        .close-btn:hover {
          color: var(--text-primary);
        }

        .modal-body {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .form-group {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .form-group label {
          font-size: 13px;
          font-weight: 600;
          color: var(--text-secondary);
        }

        .helper-text {
          font-size: 12px;
          color: var(--text-muted);
          line-height: 1.4;
        }

        .modal-footer {
          display: flex;
          justify-content: flex-end;
          gap: 12px;
          border-top: 1px solid var(--border-color);
          padding-top: 16px;
          margin-top: 8px;
        }
      `}</style>
    </div>
  );
};
