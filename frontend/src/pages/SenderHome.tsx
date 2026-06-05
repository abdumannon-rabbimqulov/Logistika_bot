import React from "react";
import { Link } from "react-router-dom";
import { Package, MapPin, Bot, MessagesSquare, Plus, List } from "lucide-react";

export const SenderHome: React.FC = () => {
  return (
    <>
      <div className="mobile-card">
        <Package size={28} style={{ color: "var(--accent-secondary)", marginBottom: 8 }} />
        <h3>Yuk beruvchi</h3>
        <p>Buyurtma berish, AI yordamchi va haydovchi bilan bog&apos;lanish.</p>
      </div>

      <Link
        to="/sender/orders/create"
        className="mobile-list-item"
        style={{ textDecoration: "none", color: "inherit" }}
      >
        <Plus size={24} style={{ color: "var(--accent-secondary)" }} />
        <div>
          <strong>Yangi buyurtma</strong>
          <p style={{ fontSize: 12, margin: "4px 0 0" }}>
            Yuk, marshrut va mashina turini kiriting
          </p>
        </div>
      </Link>

      <Link
        to="/sender/orders"
        className="mobile-list-item"
        style={{ textDecoration: "none", color: "inherit" }}
      >
        <List size={24} style={{ color: "var(--accent-primary)" }} />
        <div>
          <strong>Mening buyurtmalarim</strong>
          <p style={{ fontSize: 12, margin: "4px 0 0" }}>
            Kutilmoqda, faol va yakunlangan buyurtmalar
          </p>
        </div>
      </Link>

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

      <div className="mobile-card" style={{ opacity: 0.85 }}>
        <MapPin size={20} />
        <p style={{ marginTop: 8, fontSize: 12 }}>
          Marshrut nuqtalarida xaritadan GPS tanlash ixtiyoriy — manzil matni yetarli.
        </p>
      </div>
    </>
  );
};
