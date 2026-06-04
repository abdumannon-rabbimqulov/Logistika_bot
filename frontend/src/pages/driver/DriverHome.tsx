import React from "react";
import { Link } from "react-router-dom";
import { ChevronRight, Megaphone, Navigation, Package, Radio } from "lucide-react";
import { useLocation } from "../../context/LocationContext";
import { AvailableOrdersSection } from "../../components/driver/AvailableOrdersSection";

const menuItems = [
  {
    to: "/driver/profile",
    icon: Navigation,
    title: "Profil va sozlamalar",
    subtitle: "Mashina, reyting, GPS yoqish",
    gradient: "from-emerald-600/20 to-teal-600/10",
    iconColor: "text-emerald-400",
  },
  {
    to: "/driver/announcements",
    icon: Megaphone,
    title: "Safar e'lonlari",
    subtitle: "Marshrut e'lon qilish, takliflar",
    gradient: "from-violet-600/20 to-indigo-600/10",
    iconColor: "text-violet-400",
  },
  {
    to: "/driver/orders",
    icon: Package,
    title: "Barcha buyurtmalar",
    subtitle: "Mos keluvchi yuklar ro'yxati",
    gradient: "from-amber-600/20 to-orange-600/10",
    iconColor: "text-amber-400",
  },
];

export const DriverHome: React.FC = () => {
  const { enabled, active, toggle, error } = useLocation();

  return (
    <div className="space-y-8 pb-8">
      <div className="rounded-2xl border border-white/5 bg-slate-800/60 p-6 backdrop-blur-md shadow-xl shadow-black/30">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Haydovchi kabineti
            </p>
            <h2 className="text-xl font-bold text-white mt-1">Salom!</h2>
            <p className="text-sm text-slate-400 mt-1">Bugun liniyada bo&apos;ling</p>
          </div>
          <button
            type="button"
            onClick={toggle}
            className={`shrink-0 flex items-center gap-2 rounded-2xl px-4 py-2.5 text-sm font-semibold transition ${
              enabled
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                : "bg-white/5 text-slate-400 border border-white/10"
            }`}
          >
            <Radio size={18} className={enabled && active ? "animate-pulse" : ""} />
            GPS {enabled ? "ON" : "OFF"}
          </button>
        </div>
        {error && <p className="text-xs text-rose-400 mt-3">{error}</p>}
      </div>

      <nav className="space-y-3">
        {menuItems.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={`group flex items-center gap-4 rounded-2xl border border-white/5 bg-slate-800/40 backdrop-blur-md p-4 no-underline transition-all duration-200 hover:bg-slate-800/70 hover:border-white/10 hover:scale-[1.01] active:scale-[0.99] bg-gradient-to-r ${item.gradient}`}
          >
            <div
              className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-900/60 ${item.iconColor}`}
            >
              <item.icon size={24} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-white">{item.title}</p>
              <p className="text-xs text-slate-400 mt-0.5">{item.subtitle}</p>
            </div>
            <ChevronRight
              size={20}
              className="text-slate-600 group-hover:text-slate-300 transition"
            />
          </Link>
        ))}
      </nav>

      <AvailableOrdersSection />
    </div>
  );
};
