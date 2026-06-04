import React from "react";
import { Navigate } from "react-router-dom";

/** Buyurtmalar bosh sahifada — eski yo'nalishni saqlash */
export const DriverOrdersPage: React.FC = () => {
  return <Navigate to="/driver" replace />;
};
