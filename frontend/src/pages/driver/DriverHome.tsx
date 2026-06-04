import React from "react";
import { DriverStatusBar } from "../../components/driver/DriverStatusBar";
import { AvailableOrdersSection } from "../../components/driver/AvailableOrdersSection";

export const DriverHome: React.FC = () => {
  return (
    <div className="flex flex-col min-h-full -mt-1">
      <header className="relative shrink-0 pb-3 border-b border-white/5 mb-4">
        <DriverStatusBar />
      </header>
      <AvailableOrdersSection />
    </div>
  );
};
