import React from "react";
import { Link } from "react-router-dom";
import { Route, Megaphone, Bot } from "lucide-react";
import { DriverStatusBar } from "../../components/driver/DriverStatusBar";
import { AvailableOrdersSection } from "../../components/driver/AvailableOrdersSection";

export const DriverHome: React.FC = () => {
  const menuLinks = [
    {
      to: "/driver/trips",
      icon: Route,
      color: "from-cyan-500/20 to-blue-500/10 text-cyan-400 ring-cyan-500/30",
      title: "Safarlar",
      subtitle: "Safar va buyurtmalar tarixi",
    },
    {
      to: "/driver/announcements",
      icon: Megaphone,
      color: "from-purple-500/20 to-indigo-500/10 text-purple-400 ring-purple-500/30",
      title: "E'lonlar",
      subtitle: "Mashina bo'yicha e'lonlar",
    },
    {
      to: "/driver/ai",
      icon: Bot,
      color: "from-emerald-500/20 to-teal-500/10 text-emerald-400 ring-emerald-500/30",
      title: "AI Chat",
      subtitle: "Logistika AI yordamchisi",
    },
  ];

  return (
    <div className="flex flex-col flex-1 min-h-0 -mt-1 space-y-5">
      <header className="relative shrink-0 pb-3 border-b border-white/5 mb-1">
        <DriverStatusBar />
      </header>

      {/* QUICK ACTIONS GRID */}
      <section className="grid grid-cols-3 gap-2.5">
        {menuLinks.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className="flex flex-col items-center text-center p-3 rounded-2xl border border-white/5 bg-slate-800/40 hover:bg-slate-800/70 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98] no-underline group"
          >
            <div className={`flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br ring-1 mb-2.5 transition-all duration-300 group-hover:scale-110 ${item.color}`}>
              <item.icon size={22} />
            </div>
            <h4 className="text-xs font-bold text-white leading-tight">{item.title}</h4>
            <p className="text-[9px] text-slate-500 leading-tight mt-1">
              {item.subtitle}
            </p>
          </Link>
        ))}
      </section>

      {/* ORDERS LIST */}
      <div className="flex-1">
        <AvailableOrdersSection />
      </div>
    </div>
  );
};
