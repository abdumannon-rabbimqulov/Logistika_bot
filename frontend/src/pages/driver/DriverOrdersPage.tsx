import React from "react";
import { DriverOrdersList } from "../../components/driver/DriverOrdersList";

/** Pastki nav: Buyurtma — pending buyurtmalar ro'yxati */
export const DriverOrdersPage: React.FC = () => {
  return (
    <div className="min-h-[50vh] w-full">
      <DriverOrdersList title="Buyurtmalar" />
    </div>
  );
};
