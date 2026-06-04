import React from "react";
import { Link } from "react-router-dom";
import { Package, MapPin, Bot, MessagesSquare } from "lucide-react";

export const SenderHome: React.FC = () => {
  return (
    <>
      <div className="mobile-card">
        <Package size={28} style={{ color: "var(--accent-secondary)", marginBottom: 8 }} />
        <h3>Yuk beruvchi</h3>
        <p>Buyurtma berish, AI yordamchi va haydovchi bilan bog&apos;lanish.</p>
      </div>

      <Link to="/sender/ai" className="mobile-list-item" style={{ textDecoration: "none", color: "inherit" }}>
        <Bot size={24} style={{ color: "var(--accent-secondary)" }} />
        <div>
          <strong>AI yordamchi</strong>
          <p style={{ fontSize: 12, margin: "4px 0 0" }}>Buyurtma va logistika bo&apos;yicha savollar</p>
        </div>
      </Link>

      <Link to="/sender/chats" className="mobile-list-item" style={{ textDecoration: "none", color: "inherit" }}>
        <MessagesSquare size={24} style={{ color: "var(--accent-primary)" }} />
        <div>
          <strong>Mening chatlarim</strong>
          <p style={{ fontSize: 12, margin: "4px 0 0" }}>Haydovchi va qo&apos;llab-quvvatlash bilan yozishmalar</p>
        </div>
      </Link>

      <div className="mobile-card" style={{ opacity: 0.7 }}>
        <MapPin size={20} />
        <p style={{ marginTop: 8 }}>Tez orada: yangi buyurtma yaratish</p>
      </div>
    </>
  );
};
