import React, { useEffect, useState } from "react";
import { resolveMediaUrl } from "../../api";
import {
  fetchTruckTypes,
  fetchTruckType,
  createTruckType,
  updateTruckType,
  deleteTruckType,
  uploadTruckTypeImage,
  defaultTruckTypeForm,
  truckTypeToForm,
  sanitizeTruckTypePayload,
  validateTruckTypeForm,
  type TruckTypePayload,
} from "../../services/driverApi";
import type { TruckType } from "../../types/auth";
import { ConfirmModal } from "../../components/mobile/ConfirmModal";
import { Plus, Pencil, Trash2, ImagePlus, Eye } from "lucide-react";

function formatDims(t: TruckType): string {
  const parts: string[] = [];
  if (t.length != null) parts.push(`U: ${t.length}m`);
  if (t.width != null) parts.push(`K: ${t.width}m`);
  if (t.height != null) parts.push(`B: ${t.height}m`);
  return parts.length ? parts.join(" · ") : "";
}

export const TruckTypesAdmin: React.FC = () => {
  const [items, setItems] = useState<TruckType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [sheetOpen, setSheetOpen] = useState(false);
  const [viewItem, setViewItem] = useState<TruckType | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<TruckTypePayload>(defaultTruckTypeForm());
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setItems(await fetchTruckTypes());
    } catch (ex: unknown) {
      setError(ex instanceof Error ? ex.message : "Yuklanmadi");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openCreate = () => {
    setViewItem(null);
    setEditingId(null);
    setForm(defaultTruckTypeForm());
    setSheetOpen(true);
  };

  const openEdit = async (id: number) => {
    setError("");
    try {
      const t = await fetchTruckType(id);
      setViewItem(null);
      setEditingId(id);
      setForm(truckTypeToForm(t));
      setSheetOpen(true);
    } catch (ex: unknown) {
      setError(ex instanceof Error ? ex.message : "Xatolik");
    }
  };

  const openView = async (id: number) => {
    setError("");
    try {
      setViewItem(await fetchTruckType(id));
      setSheetOpen(false);
    } catch (ex: unknown) {
      setError(ex instanceof Error ? ex.message : "Xatolik");
    }
  };

  const setNum = (key: keyof TruckTypePayload, raw: string, required = false) => {
    const v = raw === "" ? (required ? 0 : null) : Number(raw);
    setForm((f) => ({ ...f, [key]: v }));
  };

  const handleImage = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingImage(true);
    setError("");
    try {
      const res = await uploadTruckTypeImage(file);
      setForm((f) => ({ ...f, image_url: res.url }));
    } catch (ex: unknown) {
      setError(ex instanceof Error ? ex.message : "Rasm xatoligi");
    } finally {
      setUploadingImage(false);
      e.target.value = "";
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const validation = validateTruckTypeForm(form);
    if (validation) {
      setError(validation);
      return;
    }
    const payload = sanitizeTruckTypePayload(form);
    setSaving(true);
    setError("");
    try {
      if (editingId) {
        await updateTruckType(editingId, payload);
      } else {
        await createTruckType(payload);
      }
      setSheetOpen(false);
      await load();
    } catch (ex: unknown) {
      setError(ex instanceof Error ? ex.message : "Saqlanmadi");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    setSaving(true);
    try {
      await deleteTruckType(deleteId);
      setDeleteId(null);
      if (viewItem?.id === deleteId) setViewItem(null);
      await load();
    } catch (ex: unknown) {
      setError(ex instanceof Error ? ex.message : "O'chirilmadi");
    } finally {
      setSaving(false);
    }
  };

  const renderFormFields = () => (
    <>
      <div className="mobile-field">
        <label>Nomi * (max 50)</label>
        <input
          value={form.name}
          maxLength={50}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
          placeholder="Masalan: Fura 20t"
        />
      </div>

      <div className="truck-type-form-grid">
        <div className="mobile-field">
          <label>Max og&apos;irlik (t) *</label>
          <input
            type="number"
            min={0}
            step="0.01"
            value={form.max_weight || ""}
            onChange={(e) => setNum("max_weight", e.target.value, true)}
            required
          />
        </div>
        <div className="mobile-field">
          <label>Max hajm (m³) *</label>
          <input
            type="number"
            min={0}
            step="0.01"
            value={form.max_volume || ""}
            onChange={(e) => setNum("max_volume", e.target.value, true)}
            required
          />
        </div>
        <div className="mobile-field">
          <label>Uzunlik (m)</label>
          <input
            type="number"
            min={0}
            step="0.01"
            value={form.length ?? ""}
            onChange={(e) => setNum("length", e.target.value)}
            placeholder="Ixtiyoriy"
          />
        </div>
        <div className="mobile-field">
          <label>Kenglik (m)</label>
          <input
            type="number"
            min={0}
            step="0.01"
            value={form.width ?? ""}
            onChange={(e) => setNum("width", e.target.value)}
            placeholder="Ixtiyoriy"
          />
        </div>
        <div className="mobile-field">
          <label>Balandlik (m)</label>
          <input
            type="number"
            min={0}
            step="0.01"
            value={form.height ?? ""}
            onChange={(e) => setNum("height", e.target.value)}
            placeholder="Ixtiyoriy"
          />
        </div>
        <div className="mobile-field">
          <label>Pallet sig&apos;imi (dona)</label>
          <input
            type="number"
            min={0}
            step={1}
            value={form.pallet_capacity ?? ""}
            onChange={(e) => setNum("pallet_capacity", e.target.value)}
            placeholder="Ixtiyoriy"
          />
        </div>
      </div>

      <div className="mobile-field">
        <label>Tavsif (max 200)</label>
        <textarea
          rows={3}
          maxLength={200}
          value={form.description ?? ""}
          onChange={(e) => setForm({ ...form, description: e.target.value || null })}
          placeholder="Qisqa tavsif"
        />
      </div>

      <div className="mobile-field">
        <label>Rasm (POST /truck-types/image)</label>
        <label className="mobile-btn mobile-btn-secondary" style={{ cursor: "pointer" }}>
          <ImagePlus size={18} />
          {uploadingImage ? "Yuklanmoqda..." : "Rasm yuklash"}
          <input type="file" accept="image/*" hidden onChange={handleImage} disabled={uploadingImage} />
        </label>
        <input
          type="text"
          placeholder="Yuklangan rasm yo‘li yoki URL"
          value={form.image_url ?? ""}
          onChange={(e) => setForm({ ...form, image_url: e.target.value || null })}
          style={{ marginTop: 8 }}
        />
        {form.image_url && (
          <img src={resolveMediaUrl(form.image_url)} alt="" className="truck-type-image-preview" />
        )}
      </div>

      <label className="truck-type-checkbox">
        <input
          type="checkbox"
          checked={form.is_active}
          onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
        />
        <span>Faol (is_active)</span>
      </label>
    </>
  );

  return (
    <div className="truck-types-admin">
      <div className="truck-types-toolbar">
        <h2>Mashina turlari</h2>
        <button type="button" className="btn btn-primary" onClick={openCreate}>
          <Plus size={18} /> Yangi
        </button>
      </div>

      {error && <div className="mobile-alert mobile-alert-error">{error}</div>}
      {loading && <p style={{ color: "var(--text-muted)" }}>Yuklanmoqda...</p>}

      <div className="truck-types-list">
        {items.map((t) => (
          <article key={t.id} className="truck-type-card">
            {t.image_url ? (
              <img src={resolveMediaUrl(t.image_url)} alt={t.name} />
            ) : (
              <div className="truck-type-thumb">Rasm yo&apos;q</div>
            )}
            <div className="truck-type-card-body">
              <strong>{t.name}</strong>
              <p className="truck-type-meta">
                {t.max_weight} t · {t.max_volume} m³
                {t.pallet_capacity != null ? ` · ${t.pallet_capacity} pallet` : ""}
              </p>
              {formatDims(t) && <p className="truck-type-meta">{formatDims(t)}</p>}
              {t.description && (
                <p className="truck-type-meta" style={{ marginTop: 4 }}>
                  {t.description}
                </p>
              )}
              <span className={`truck-type-badge ${t.is_active ? "active" : "inactive"}`}>
                {t.is_active ? "Faol" : "Nofaol"}
              </span>
            </div>
            <div className="truck-type-actions">
              <button type="button" className="icon-btn-mobile" onClick={() => openView(t.id)} aria-label="Ko'rish">
                <Eye size={18} />
              </button>
              <button type="button" className="icon-btn-mobile" onClick={() => openEdit(t.id)} aria-label="Tahrir">
                <Pencil size={18} />
              </button>
              <button
                type="button"
                className="icon-btn-mobile danger"
                onClick={() => setDeleteId(t.id)}
                aria-label="O'chirish"
              >
                <Trash2 size={18} />
              </button>
            </div>
          </article>
        ))}
      </div>

      {viewItem && (
        <div className="mobile-modal-backdrop" onClick={() => setViewItem(null)}>
          <div className="mobile-modal-sheet truck-type-sheet" onClick={(e) => e.stopPropagation()}>
            <h3>{viewItem.name}</h3>
            <p className="sheet-hint">GET /drivers/truck-types/{viewItem.id}</p>
            {viewItem.image_url && (
              <img
                src={resolveMediaUrl(viewItem.image_url)}
                alt=""
                className="truck-type-image-preview"
                style={{ marginBottom: 12 }}
              />
            )}
            <dl className="truck-type-detail-dl">
              <dt>Max og&apos;irlik</dt>
              <dd>{viewItem.max_weight} t</dd>
              <dt>Max hajm</dt>
              <dd>{viewItem.max_volume} m³</dd>
              {viewItem.length != null && (
                <>
                  <dt>Uzunlik</dt>
                  <dd>{viewItem.length} m</dd>
                </>
              )}
              {viewItem.width != null && (
                <>
                  <dt>Kenglik</dt>
                  <dd>{viewItem.width} m</dd>
                </>
              )}
              {viewItem.height != null && (
                <>
                  <dt>Balandlik</dt>
                  <dd>{viewItem.height} m</dd>
                </>
              )}
              {viewItem.pallet_capacity != null && (
                <>
                  <dt>Pallet</dt>
                  <dd>{viewItem.pallet_capacity}</dd>
                </>
              )}
              <dt>Holat</dt>
              <dd>{viewItem.is_active ? "Faol" : "Nofaol"}</dd>
              {viewItem.description && (
                <>
                  <dt>Tavsif</dt>
                  <dd>{viewItem.description}</dd>
                </>
              )}
              {viewItem.image_url && (
                <>
                  <dt>image_url</dt>
                  <dd style={{ wordBreak: "break-all", fontSize: 11 }}>{viewItem.image_url}</dd>
                </>
              )}
            </dl>
            <button type="button" className="mobile-btn mobile-btn-primary" onClick={() => openEdit(viewItem.id)}>
              Tahrirlash
            </button>
            <button type="button" className="mobile-btn mobile-btn-secondary" style={{ marginTop: 8 }} onClick={() => setViewItem(null)}>
              Yopish
            </button>
          </div>
        </div>
      )}

      {sheetOpen && (
        <div className="mobile-modal-backdrop" onClick={() => setSheetOpen(false)}>
          <div className="mobile-modal-sheet truck-type-sheet" onClick={(e) => e.stopPropagation()}>
            <h3>{editingId ? "Mashina turini tahrirlash" : "Yangi mashina turi"}</h3>
            <p className="sheet-hint">
              {editingId ? "PATCH" : "POST"} /drivers/truck-types{editingId ? `/${editingId}` : ""}
            </p>
            <form className="mobile-form" onSubmit={handleSave}>
              {renderFormFields()}
              <button type="submit" className="mobile-btn mobile-btn-primary" disabled={saving || uploadingImage}>
                {saving ? "Saqlanmoqda..." : "Saqlash"}
              </button>
              <button
                type="button"
                className="mobile-btn mobile-btn-secondary"
                onClick={() => setSheetOpen(false)}
                disabled={saving}
              >
                Bekor qilish
              </button>
            </form>
          </div>
        </div>
      )}

      <ConfirmModal
        open={deleteId !== null}
        title="O'chirish"
        message="Ushbu mashina turini o'chirasizmi?"
        danger
        onConfirm={handleDelete}
        onCancel={() => setDeleteId(null)}
      />

      <style>{`
        .truck-type-detail-dl {
          display: grid;
          grid-template-columns: 120px 1fr;
          gap: 8px 12px;
          font-size: 14px;
          margin-bottom: 16px;
        }
        .truck-type-detail-dl dt {
          color: var(--text-muted);
          font-weight: 600;
        }
        .truck-type-detail-dl dd {
          margin: 0;
          color: var(--text-primary);
        }
        .mobile-field textarea {
          width: 100%;
          min-height: 72px;
          padding: 12px 14px;
          font-size: 16px;
          border-radius: var(--border-radius);
          border: 1px solid var(--border-color);
          background: rgba(255, 255, 255, 0.04);
          color: var(--text-primary);
          resize: vertical;
          font-family: inherit;
        }
      `}</style>
    </div>
  );
};
