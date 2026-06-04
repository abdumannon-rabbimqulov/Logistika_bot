import React from "react";
import { Outlet, useNavigate, useLocation, NavLink } from "react-router-dom";
import { ArrowLeft, Home, User, Bot, MessagesSquare } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import type { UserRole } from "../types/auth";

interface MobileAppLayoutProps {
  role: "sender" | "driver";
  title?: string;
}

function pageTitle(pathname: string, role: "sender" | "driver", override?: string): string {
  if (override) return override;
  if (pathname.endsWith("/profile")) return "Profil";
  if (role === "sender") {
    if (pathname.includes("/ai")) return "AI yordamchi";
    if (pathname.match(/\/chats\/\d+/)) return "Chat";
    if (pathname.endsWith("/chats")) return "Chatlar";
    return "Yuk beruvchi";
  }
  return "Haydovchi";
}

export const MobileAppLayout: React.FC<MobileAppLayoutProps> = ({ role, title }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();

  const base = role === "sender" ? "/sender" : "/driver";
  const pathname = location.pathname;
  const isHome = pathname === base || pathname === `${base}/`;
  const isProfile = pathname.endsWith("/profile");
  const isAi = pathname.includes("/ai");
  const isChatsList = pathname.endsWith("/chats");
  const isChatDetail = /\/chats\/\d+/.test(pathname);

  const headerTitle = pageTitle(pathname, role, title);

  const showBack = !isHome && (isProfile || isAi || isChatsList || isChatDetail);

  const goBack = () => {
    if (isChatDetail) navigate(`${base}/chats`);
    else if (isAi || isChatsList) navigate(base);
    else navigate(base);
  };

  return (
    <div className="mobile-app-root">
      <div className="mobile-phone">
        <header className="mobile-header">
          {showBack ? (
            <button type="button" className="back-btn" onClick={goBack} aria-label="Orqaga">
              <ArrowLeft size={20} />
            </button>
          ) : (
            <div style={{ width: 40 }} />
          )}
          <h1>{headerTitle}</h1>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
            {user?.full_name?.split(" ")[0] || "—"}
          </span>
        </header>

        <main className={`mobile-content${isAi ? " no-nav" : ""}`}>
          <Outlet />
        </main>

        {!isAi && (
        <nav className="mobile-bottom-nav">
          <NavLink to={base} end className={({ isActive }) => `mobile-nav-item${isActive ? " active" : ""}`}>
            <Home size={22} />
            <span>Bosh</span>
          </NavLink>
          {role === "sender" && (
            <>
              <NavLink
                to={`${base}/ai`}
                className={({ isActive }) => `mobile-nav-item${isActive ? " active" : ""}`}
              >
                <Bot size={22} />
                <span>AI</span>
              </NavLink>
              <NavLink
                to={`${base}/chats`}
                className={({ isActive }) =>
                  `mobile-nav-item${isActive || isChatDetail ? " active" : ""}`
                }
              >
                <MessagesSquare size={22} />
                <span>Chat</span>
              </NavLink>
            </>
          )}
          <NavLink
            to={`${base}/profile`}
            className={({ isActive }) => `mobile-nav-item${isActive ? " active" : ""}`}
          >
            <User size={22} />
            <span>Profil</span>
          </NavLink>
        </nav>
        )}
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
