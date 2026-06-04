import React from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Home, Megaphone, User, Package } from "lucide-react";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `flex flex-1 flex-col items-center justify-center gap-1 rounded-2xl py-2.5 mx-0.5 transition-all duration-200 ${
    isActive
      ? "bg-white/10 text-white shadow-inner"
      : "text-slate-500 hover:text-slate-300 hover:bg-white/5"
  }`;

export const DriverBottomNav: React.FC = () => {
  const { pathname } = useLocation();
  const annActive = pathname.includes("/announcements");

  return (
    <nav className="shrink-0 border-t border-white/5 bg-slate-900/95 backdrop-blur-xl px-2 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
      <div className="flex gap-1 max-w-lg mx-auto">
        <NavLink to="/driver" end className={linkClass}>
          <Home size={22} />
          <span className="text-[10px] font-medium">Bosh</span>
        </NavLink>
        <NavLink to="/driver/orders" className={linkClass}>
          <Package size={22} />
          <span className="text-[10px] font-medium">Buyurtma</span>
        </NavLink>
        <NavLink to="/driver/announcements" className={({ isActive }) => linkClass({ isActive: isActive || annActive })}>
          <Megaphone size={22} />
          <span className="text-[10px] font-medium">E&apos;lon</span>
        </NavLink>
        <NavLink to="/driver/profile" className={linkClass}>
          <User size={22} />
          <span className="text-[10px] font-medium">Profil</span>
        </NavLink>
      </div>
    </nav>
  );
};
