import React from "react";

interface ConfirmModalProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  open,
  title,
  message,
  confirmLabel = "Ha",
  cancelLabel = "Bekor qilish",
  danger = false,
  onConfirm,
  onCancel,
}) => {
  if (!open) return null;

  return (
    <div className="mobile-modal-backdrop" onClick={onCancel}>
      <div className="mobile-modal-sheet" onClick={(e) => e.stopPropagation()}>
        <h3 style={{ marginBottom: 8 }}>{title}</h3>
        <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 20 }}>{message}</p>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <button
            type="button"
            className={`mobile-btn ${danger ? "mobile-btn-danger" : "mobile-btn-primary"}`}
            onClick={onConfirm}
          >
            {confirmLabel}
          </button>
          <button type="button" className="mobile-btn mobile-btn-secondary" onClick={onCancel}>
            {cancelLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
