import React, { useEffect, useState } from "react";
import { resolveMediaUrl } from "../../api";
import {
  createTruckType,
  defaultTruckTypeForm,
  deleteTruckType,
  fetchTruckTypes,
  sanitizeTruckTypePayload,
  truckTypeToForm,
  updateTruckType,
  uploadTruckTypeImage,
  validateTruckTypeForm,
  type TruckTypePayload,
} from "../../services/driverApi";
import type { TruckType } from "../../types/auth";
import { Modal } from "../../components/ui/Modal";
import { ImageDropzone } from "../../components/ui/ImageDropzone";
import { TruckTypeCardSkeleton } from "../../components/ui/Skeleton";
import { useToast } from "../../components/ui/Toast";
import {
  Plus,
  Pencil,
  Trash2,
  Weight,
  Box,
  Ruler,
  Layers,
  Package,
} from "lucide-react";

export const TruckTypesAdmin: React.FC = () => {
  const { toast } = useToast();
  const [items, setItems] = useState<TruckType[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<TruckTypePayload>(defaultTruckTypeForm());
  const [saving, setSaving] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setItems(await fetchTruckTypes());
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Yuklanmadi", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openCreate = () => {
    setEditingId(null);
    setForm(defaultTruckTypeForm());
    setModalOpen(true);
  };

  const openEdit = (t: TruckType) => {
    setEditingId(t.id);
    setForm(truckTypeToForm(t));
    setModalOpen(true);
  };

  const handleImageUpload = async (file: File) => {
    setUploadingImage(true);
    try {
      const res = await uploadTruckTypeImage(file);
      setForm((f) => ({ ...f, image_url: res.url }));
      toast("Rasm yuklandi", "success");
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Rasm xatoligi", "error");
    } finally {
      setUploadingImage(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const err = validateTruckTypeForm(form);
    if (err) {
      toast(err, "error");
      return;
    }
    const payload = sanitizeTruckTypePayload(form);
    setSaving(true);
    try {
      if (editingId) await updateTruckType(editingId, payload);
      else await createTruckType(payload);
      toast(editingId ? "Yangilandi" : "Qo'shildi", "success");
      setModalOpen(false);
      await load();
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Saqlanmadi", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    try {
      await deleteTruckType(deleteId);
      toast("O'chirildi", "success");
      setDeleteId(null);
      await load();
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "O'chirilmadi", "error");
    }
  };

  const setNum = (key: keyof TruckTypePayload, raw: string, required = false) => {
    const v = raw === "" ? (required ? 0 : null) : Number(raw);
    setForm((f) => ({ ...f, [key]: v }));
  };

  return (
    <div className="min-h-full text-slate-100">
      <div className="flex flex-wrap items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Mashina turlari</h1>
          <p className="text-sm text-slate-400 mt-1">Admin boshqaruvi · GET/POST/PATCH truck-types</p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-cyan-500 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-violet-500/25 hover:opacity-90 transition"
        >
          <Plus size={18} /> Yangi tur
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <TruckTypeCardSkeleton key={i} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-600 bg-slate-800/30 py-16 text-center text-slate-400">
          Ma&apos;lumot topilmadi. Yangi mashina turi qo&apos;shing.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {items.map((t) => (
            <article
              key={t.id}
              className="group rounded-2xl border border-slate-700/80 bg-slate-800/60 overflow-hidden hover:border-cyan-500/40 hover:shadow-xl hover:shadow-cyan-500/5 transition-all duration-300"
            >
              <div className="relative h-40 bg-slate-900/80">
                {t.image_url ? (
                  <img
                    src={resolveMediaUrl(t.image_url)}
                    alt={t.name}
                    className="h-full w-full object-cover"
                  />
                ) : (
                  <div className="flex h-full items-center justify-center text-slate-500">
                    <Package size={48} strokeWidth={1} />
                  </div>
                )}
                <span
                  className={`absolute top-3 right-3 rounded-full px-2.5 py-0.5 text-xs font-bold ${
                    t.is_active ? "bg-emerald-500/20 text-emerald-300" : "bg-rose-500/20 text-rose-300"
                  }`}
                >
                  {t.is_active ? "Faol" : "Nofaol"}
                </span>
              </div>
              <div className="p-4 space-y-3">
                <h3 className="font-bold text-lg">{t.name}</h3>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center gap-1.5 text-slate-300">
                    <Weight size={14} className="text-amber-400" />
                    {t.max_weight} t
                  </div>
                  <div className="flex items-center gap-1.5 text-slate-300">
                    <Box size={14} className="text-cyan-400" />
                    {t.max_volume} m³
                  </div>
                  {(t.length || t.width || t.height) && (
                    <div className="col-span-2 flex items-center gap-1.5 text-slate-400">
                      <Ruler size={14} className="text-violet-400" />
                      {[t.length && `U:${t.length}m`, t.width && `K:${t.width}m`, t.height && `B:${t.height}m`]
                        .filter(Boolean)
                        .join(" · ")}
                    </div>
                  )}
                  {t.pallet_capacity != null && (
                    <div className="flex items-center gap-1.5 text-slate-400">
                      <Layers size={14} />
                      {t.pallet_capacity} pallet
                    </div>
                  )}
                </div>
                <div className="flex gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => openEdit(t)}
                    className="flex-1 inline-flex items-center justify-center gap-1 rounded-lg border border-slate-600 py-2 text-sm hover:bg-slate-700 transition"
                  >
                    <Pencil size={16} /> Tahrir
                  </button>
                  <button
                    type="button"
                    onClick={() => setDeleteId(t.id)}
                    className="rounded-lg border border-rose-500/40 px-3 py-2 text-rose-400 hover:bg-rose-500/10 transition"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingId ? "Mashina turini tahrirlash" : "Yangi mashina turi"}
        wide
      >
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-400">Nomi *</label>
            <input
              className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-white"
              value={form.name}
              maxLength={50}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400">Max og&apos;irlik (t) *</label>
              <input
                type="number"
                step="0.01"
                className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-white"
                value={form.max_weight || ""}
                onChange={(e) => setNum("max_weight", e.target.value, true)}
                required
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Max hajm (m³) *</label>
              <input
                type="number"
                step="0.01"
                className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-white"
                value={form.max_volume || ""}
                onChange={(e) => setNum("max_volume", e.target.value, true)}
                required
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Uzunlik (m)</label>
              <input
                type="number"
                step="0.01"
                className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-white"
                value={form.length ?? ""}
                onChange={(e) => setNum("length", e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Kenglik (m)</label>
              <input
                type="number"
                step="0.01"
                className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-white"
                value={form.width ?? ""}
                onChange={(e) => setNum("width", e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Balandlik (m)</label>
              <input
                type="number"
                step="0.01"
                className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-white"
                value={form.height ?? ""}
                onChange={(e) => setNum("height", e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Pallet</label>
              <input
                type="number"
                className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-white"
                value={form.pallet_capacity ?? ""}
                onChange={(e) => setNum("pallet_capacity", e.target.value)}
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-400">Tavsif</label>
            <textarea
              rows={2}
              maxLength={200}
              className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-white"
              value={form.description ?? ""}
              onChange={(e) => setForm({ ...form, description: e.target.value || null })}
            />
          </div>
          <ImageDropzone
            imageUrl={form.image_url ?? null}
            onUpload={handleImageUpload}
            onUrlChange={(url) => setForm({ ...form, image_url: url })}
            uploading={uploadingImage}
          />
          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
              className="rounded"
            />
            Faol (is_active)
          </label>
          <button
            type="submit"
            disabled={saving || uploadingImage}
            className="w-full rounded-xl bg-gradient-to-r from-violet-600 to-cyan-500 py-3 font-semibold text-white disabled:opacity-50"
          >
            {saving ? "Saqlanmoqda..." : "Saqlash"}
          </button>
        </form>
      </Modal>

      <Modal open={deleteId !== null} onClose={() => setDeleteId(null)} title="O'chirish">
        <p className="text-slate-300 mb-4">Ushbu mashina turini o&apos;chirasizmi?</p>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={() => setDeleteId(null)}
            className="flex-1 rounded-lg border border-slate-600 py-2.5"
          >
            Bekor
          </button>
          <button
            type="button"
            onClick={handleDelete}
            className="flex-1 rounded-lg bg-rose-600 py-2.5 font-semibold text-white"
          >
            O&apos;chirish
          </button>
        </div>
      </Modal>
    </div>
  );
};
