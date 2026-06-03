import React from "react";
import { Link } from "react-router-dom";
import { Package, MapPin, MessageCircle } from "lucide-react";

export const SenderHome: React.FC = () => {
  return (
    <>
      <div className="mobile-card">
        <Package size={28} style={{ color: "var(--accent-secondary)", marginBottom: 8 }} />
        <h3>Yuk beruvchi</h3>
        <p>Buyurtma berish, AI yordamchi va haydovchi bilan bog&apos;lanish shu yerda bo&apos;ladi.</p>
      </div>

      <Link to="/sender/profile" className="mobile-list-item" style={{ textDecoration: "none", color: "inherit" }}>
        <MessageCircle size={24} style={{ color: "var(--accent-primary)" }} />
        <div>
          <strong>Profil va sozlamalar</strong>
          <p style={{ fontSize: 12, margin: "4px 0 0" }}>Ism, parol, chiqish</p>
        </div>
      </Link>

      <div className="mobile-card" style={{ opacity: 0.7 }}>
        <MapPin size={20} />
        <p style={{ marginTop: 8 }}>Tez orada: yangi buyurtma yaratish</p>
      </div>
    </>
  );
};
