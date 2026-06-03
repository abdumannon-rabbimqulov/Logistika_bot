import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  LayoutDashboard,
  Truck,
  Users,
  Cpu,
  MapPin,
  User,
  LogOut,
  Navigation,
} from "lucide-react";

interface SidebarProps {
  className?: string;
}

export const Sidebar: React.FC<SidebarProps> = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const navItems = [
    { to: "/dashboard", label: "Boshqaruv Paneli", icon: LayoutDashboard },
    { to: "/orders", label: "Buyurtmalar", icon: Truck },
    { to: "/users", label: "Foydalanuvchilar", icon: Users },
    { to: "/ai-commands", label: "AI Loglar", icon: Cpu },
    { to: "/live-tracking", label: "Jonli Kuzatuv", icon: MapPin },
    { to: "/profile", label: "Profil Sozlamalari", icon: User },
  ];

  return (
    <aside className="sidebar glass-card">
      <div className="sidebar-logo">
        <Navigation className="logo-icon" size={28} />
        <div>
          <h2>Logistika AI</h2>
          <span>Admin Panel</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `nav-link ${isActive ? "active" : ""}`
              }
            >
              <Icon size={20} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="user-info">
          <div className="avatar">
            {user?.full_name.charAt(0).toUpperCase() || "A"}
          </div>
          <div className="user-details">
            <h4>{user?.full_name || "Admin"}</h4>
            <span className="badge badge-primary">
              {user?.role?.toUpperCase() || "ADMIN"}
            </span>
          </div>
        </div>
        <button className="btn btn-secondary logout-btn" onClick={handleLogout}>
          <LogOut size={18} />
          <span>Chiqish</span>
        </button>
      </div>

      <style>{`
        .sidebar {
          width: var(--sidebar-width);
          height: calc(100vh - 40px);
          position: sticky;
          top: 20px;
          display: flex;
          flex-direction: column;
          padding: 24px;
          margin: 20px;
          border-radius: var(--border-radius-lg);
          z-index: 10;
        }

        .sidebar-logo {
          display: flex;
          align-items: center;
          gap: 12px;
          padding-bottom: 24px;
          border-bottom: 1px solid var(--border-color);
          margin-bottom: 24px;
        }

        .logo-icon {
          color: var(--accent-secondary);
          filter: drop-shadow(0 0 8px var(--accent-secondary-glow));
          animation: pulse 2s infinite ease-in-out;
        }

        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 1; }
          50% { transform: scale(1.05); opacity: 0.8; }
        }

        .sidebar-logo h2 {
          font-size: 18px;
          font-weight: 700;
          line-height: 1.2;
          background: linear-gradient(90deg, #fff 0%, var(--text-secondary) 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        .sidebar-logo span {
          font-size: 11px;
          font-weight: 600;
          color: var(--accent-secondary);
          text-transform: uppercase;
          letter-spacing: 0.1em;
        }

        .sidebar-nav {
          display: flex;
          flex-direction: column;
          gap: 8px;
          flex: 1;
        }

        .nav-link {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          border-radius: var(--border-radius);
          color: var(--text-secondary);
          text-decoration: none;
          font-size: 14px;
          font-weight: 500;
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .nav-link:hover {
          color: var(--text-primary);
          background: rgba(255, 255, 255, 0.05);
          transform: translateX(4px);
        }

        .nav-link.active {
          color: var(--text-primary);
          background: linear-gradient(135deg, var(--accent-primary) 0%, rgba(88, 101, 242, 0.3) 100%);
          box-shadow: 0 4px 15px rgba(88, 101, 242, 0.25);
          border-left: 3px solid var(--accent-secondary);
        }

        .sidebar-footer {
          margin-top: auto;
          padding-top: 20px;
          border-top: 1px solid var(--border-color);
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        .user-info {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .avatar {
          width: 40px;
          height: 40px;
          border-radius: 50%;
          background: linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          color: white;
          box-shadow: 0 0 10px rgba(88, 101, 242, 0.3);
        }

        .user-details h4 {
          font-size: 14px;
          font-weight: 600;
          color: var(--text-primary);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          max-width: 140px;
        }

        .logout-btn {
          width: 100%;
          justify-content: center;
          padding: 10px;
          border-color: rgba(255, 23, 68, 0.2);
          color: #ff8a80;
        }

        .logout-btn:hover {
          background: rgba(255, 23, 68, 0.1);
          color: #ff1744;
          border-color: rgba(255, 23, 68, 0.4);
        }
      `}</style>
    </aside>
  );
};
