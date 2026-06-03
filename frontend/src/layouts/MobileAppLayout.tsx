import React from "react";
import { Outlet, useNavigate, useLocation, NavLink } from "react-router-dom";
import { ArrowLeft, Home, User } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import type { UserRole } from "../types/auth";

interface MobileAppLayoutProps {
  role: "sender" | "driver";
  title?: string;
}

export const MobileAppLayout: React.FC<MobileAppLayoutProps> = ({ role, title }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();

  const base = role === "sender" ? "/sender" : "/driver";
  const isProfile = location.pathname.endsWith("/profile");
  const pageTitle =
    title ||
    (isProfile ? "Profil" : role === "sender" ? "Yuk beruvchi" : "Haydovchi");

  const showBack = isProfile;

  return (
    <div className="mobile-app-root">
      <div className="mobile-phone">
        <header className="mobile-header">
          {showBack ? (
            <button type="button" className="back-btn" onClick={() => navigate(base)} aria-label="Orqaga">
              <ArrowLeft size={20} />
            </button>
          ) : (
            <div style={{ width: 40 }} />
          )}
          <h1>{pageTitle}</h1>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
            {user?.full_name?.split(" ")[0] || "—"}
          </span>
        </header>

        <main className="mobile-content">
          <Outlet />
        </main>

        <nav className="mobile-bottom-nav">
          <NavLink to={base} end className={({ isActive }) => `mobile-nav-item${isActive ? " active" : ""}`}>
            <Home size={22} />
            <span>Bosh sahifa</span>
          </NavLink>
          <NavLink
            to={`${base}/profile`}
            className={({ isActive }) => `mobile-nav-item${isActive ? " active" : ""}`}
          >
            <User size={22} />
            <span>Profil</span>
          </NavLink>
        </nav>
      </div>
    </div>
  );
};

export function roleNavBase(role: UserRole): string {
  if (role === "sender") return "/sender";
  if (role === "driver") return "/driver";
  if (role === "admin") return "/dashboard";
  return "/login";
}
