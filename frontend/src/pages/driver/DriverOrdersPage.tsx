import React from "react";
import { AvailableOrdersSection } from "../../components/driver/AvailableOrdersSection";

export const DriverOrdersPage: React.FC = () => {
  return (
    <div>
      <p className="text-sm text-slate-400 mb-4">
        Sizning mashina turiga mos, kutilayotgan buyurtmalar. Taklif POST /orders/&#123;id&#125;/offers
      </p>
      <AvailableOrdersSection />
    </div>
  );
};
