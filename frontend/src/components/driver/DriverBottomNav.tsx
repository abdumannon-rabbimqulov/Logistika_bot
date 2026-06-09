import React from "react";
import { NavLink } from "react-router-dom";
import { Home, MessageSquare, User } from "lucide-react";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `flex flex-1 flex-col items-center justify-center gap-1 rounded-2xl py-2.5 mx-0.5 transition-all duration-200 ${
    isActive
      ? "bg-white/10 text-white shadow-inner"
      : "text-slate-500 hover:text-slate-300 hover:bg-white/5"
  }`;

export const DriverBottomNav: React.FC = () => {
  return (
    <nav className="shrink-0 border-t border-white/5 bg-slate-900/95 backdrop-blur-xl px-2 pt-2 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
      <div className="flex gap-1 max-w-lg mx-auto">
        <NavLink to="/driver" end className={linkClass}>
          <Home size={22} />
          <span className="text-[10px] font-medium">Bosh</span>
        </NavLink>
        <NavLink to="/driver/chats" className={linkClass}>
          <MessageSquare size={22} />
          <span className="text-[10px] font-medium">Chat</span>
        </NavLink>
        <NavLink to="/driver/profile" className={linkClass}>
          <User size={22} />
          <span className="text-[10px] font-medium">Profil</span>
        </NavLink>
      </div>
    </nav>
  );
};
