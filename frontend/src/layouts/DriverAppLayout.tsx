import React from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { GpsStatusDot } from "../components/driver/GpsStatusDot";
import { DriverBottomNav } from "../components/driver/DriverBottomNav";

function titleForPath(pathname: string): string {
  if (pathname === "/driver" || pathname === "/driver/") return "Kabinet";
  if (pathname.endsWith("/profile")) return "Profil";
  if (pathname.endsWith("/orders")) return "Buyurtmalar";
  if (pathname.includes("/announcements/")) return "Takliflar";
  if (pathname.endsWith("/announcements")) return "E'lonlar";
  return "Haydovchi";
}

export const DriverAppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  const pathname = location.pathname;
  const isHome = pathname === "/driver" || pathname === "/driver/";
  const showBack = !isHome;

  return (
    <div className="min-h-[100dvh] bg-slate-900 text-slate-100 flex justify-center">
      <div className="w-full max-w-md flex flex-col min-h-[100dvh] shadow-2xl shadow-black/60 border-x border-white/5 bg-slate-900">
        <header className="sticky top-0 z-50 flex items-center gap-3 px-4 py-3.5 pt-[max(0.75rem,env(safe-area-inset-top))] bg-slate-900/90 backdrop-blur-md border-b border-white/5">
          {showBack ? (
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/5 hover:bg-white/10 transition"
              aria-label="Orqaga"
            >
              <ArrowLeft size={20} />
            </button>
          ) : (
            <div className="w-10" />
          )}
          <div className="flex-1 min-w-0">
            <h1 className="text-base font-semibold truncate">{titleForPath(pathname)}</h1>
            <p className="text-xs text-slate-500 truncate">
              {user?.full_name || "Haydovchi"}
            </p>
          </div>
          <GpsStatusDot />
        </header>

        <main className="flex-1 overflow-y-auto px-4 py-5 pb-8 space-y-1">
          <Outlet />
        </main>

        <DriverBottomNav />
      </div>
    </div>
  );
};
