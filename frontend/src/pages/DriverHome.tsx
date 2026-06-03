import React from "react";
import { Link } from "react-router-dom";
import { Truck, Navigation, Radio } from "lucide-react";

export const DriverHome: React.FC = () => {
  return (
    <>
      <div className="mobile-card">
        <Truck size={28} style={{ color: "var(--success)", marginBottom: 8 }} />
        <h3>Haydovchi paneli</h3>
        <p>Buyurtmalar, jonli GPS va e&apos;lonlar.</p>
      </div>

      <Link to="/driver/profile" className="mobile-list-item" style={{ textDecoration: "none", color: "inherit" }}>
        <Navigation size={24} style={{ color: "var(--accent-secondary)" }} />
        <div>
          <strong>Profil</strong>
          <p style={{ fontSize: 12, margin: "4px 0 0" }}>Shaxsiy ma&apos;lumotlar</p>
        </div>
      </Link>

      <div className="mobile-card">
        <Radio size={20} style={{ color: "var(--success)" }} />
        <p style={{ marginTop: 8 }}>Liniyaga chiqish va GPS — tez orada</p>
      </div>
    </>
  );
};
