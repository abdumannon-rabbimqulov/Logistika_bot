import React from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { DriverBottomNav } from "../components/driver/DriverBottomNav";

function titleForPath(pathname: string): string {
  if (pathname.endsWith("/profile")) return "Profil";
  if (pathname.endsWith("/trips")) return "Safarlar";
  if (pathname.endsWith("/orders")) return "Buyurtmalar";
  if (pathname.includes("/announcements/")) return "Takliflar";
  if (pathname.endsWith("/announcements")) return "E'lonlar";
  return "";
}

export const DriverAppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const pathname = location.pathname;
  const isHome = pathname === "/driver" || pathname === "/driver/";
  const showBack = !isHome;
  const title = titleForPath(pathname);

  return (
    <div className="min-h-[100dvh] bg-slate-900 text-slate-100 flex justify-center">
      <div className="w-full max-w-md flex flex-col min-h-[100dvh] shadow-2xl shadow-black/60 border-x border-white/5 bg-slate-900">
        {!isHome && (
          <header className="sticky top-0 z-50 flex items-center gap-3 px-4 py-3 pt-[max(0.75rem,env(safe-area-inset-top))] bg-slate-900/95 backdrop-blur-md border-b border-white/5">
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
            <h1 className="flex-1 text-base font-semibold truncate">{title}</h1>
          </header>
        )}

        <main
          className={`flex-1 overflow-y-auto ${
            isHome ? "px-4 pt-[max(0.75rem,env(safe-area-inset-top))] pb-4" : "px-4 py-5 pb-8"
          }`}
        >
          <Outlet />
        </main>

        <DriverBottomNav />
      </div>
    </div>
  );
};
