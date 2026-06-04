import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createAnnouncement,
  fetchAnnouncements,
  fetchDriverMe,
} from "../../services/driverApi";
import { useToast } from "../../components/ui/Toast";
import { Modal } from "../../components/ui/Modal";
import { Skeleton } from "../../components/ui/Skeleton";
import type { AnnouncementWaypoint, AnnouncementWaypointType } from "../../types/driver";
import { Megaphone, Plus, MapPin, Trash2, ChevronRight } from "lucide-react";

const defaultWp = (seq: number, type: AnnouncementWaypointType): AnnouncementWaypoint => ({
  sequence: seq,
  waypoint_type: type,
  city: "",
  region: "",
});

export const AnnouncementsPage: React.FC = () => {
  const { toast } = useToast();
  const [driverId, setDriverId] = useState<number | null>(null);
  const [list, setList] = useState<Awaited<ReturnType<typeof fetchAnnouncements>>>([]);
  const [loading, setLoading] = useState(true);
  const [createOpen, setCreateOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const [price, setPrice] = useState("");
  const [description, setDescription] = useState("");
  const [departureDate, setDepartureDate] = useState("");
  const [weight, setWeight] = useState("");
  const [volume, setVolume] = useState("");
  const [waypoints, setWaypoints] = useState<AnnouncementWaypoint[]>([
    defaultWp(1, "origin"),
    defaultWp(2, "destination"),
  ]);

  const load = async (did: number) => {
    setLoading(true);
    try {
      setList(await fetchAnnouncements(did));
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Yuklanmadi", "error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDriverMe()
      .then(async (p) => {
        setDriverId(p.id);
        await load(p.id);
      })
      .catch((ex: unknown) => {
        toast(ex instanceof Error ? ex.message : "Profil kerak", "error");
        setLoading(false);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addWaypoint = () => {
    setWaypoints((wps) => [...wps, defaultWp(wps.length + 1, "transit")]);
  };

  const removeWaypoint = (idx: number) => {
    if (waypoints.length <= 2) return;
    setWaypoints((wps) => wps.filter((_, i) => i !== idx).map((w, i) => ({ ...w, sequence: i + 1 })));
  };

  const updateWp = (idx: number, patch: Partial<AnnouncementWaypoint>) => {
    setWaypoints((wps) => wps.map((w, i) => (i === idx ? { ...w, ...patch } : w)));
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!driverId) return;
    if (!price || !departureDate || waypoints.some((w) => !w.city.trim())) {
      toast("Narx, sana va barcha shaharlar to'ldirilsin", "error");
      return;
    }
    setSaving(true);
    try {
      await createAnnouncement({
        driver_id: driverId,
        price: Number(price),
        currency: "UZS",
        available_weight: weight ? Number(weight) : null,
        available_volume: volume ? Number(volume) : null,
        departure_date: new Date(departureDate).toISOString(),
        description: description || null,
        waypoints: waypoints.map((w) => ({
          sequence: w.sequence,
          waypoint_type: w.waypoint_type,
          city: w.city.trim(),
          region: w.region?.trim() || null,
        })),
      });
      toast("E'lon yaratildi", "success");
      setCreateOpen(false);
      await load(driverId);
    } catch (ex: unknown) {
      toast(ex instanceof Error ? ex.message : "Xatolik", "error");
    } finally {
      setSaving(false);
    }
  };

  const routeLabel = (wps: AnnouncementWaypoint[]) =>
    wps
      .sort((a, b) => a.sequence - b.sequence)
      .map((w) => w.city)
      .filter(Boolean)
      .join(" → ");

  return (
    <div className="space-y-4 pb-6">
      <button
        type="button"
        onClick={() => setCreateOpen(true)}
        className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-cyan-500 py-3 font-semibold text-white shadow-lg"
      >
        <Plus size={20} /> Safar e&apos;loni berish
      </button>

      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : list.length === 0 ? (
        <p className="text-center text-slate-400 py-8 text-sm">E&apos;lonlar yo&apos;q</p>
      ) : (
        list.map((a) => (
          <Link
            key={a.id}
            to={`/driver/announcements/${a.id}`}
            className="block rounded-2xl border border-slate-700/80 bg-slate-800/60 p-4 hover:border-cyan-500/40 transition no-underline text-inherit"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-bold text-white flex items-center gap-2">
                  <Megaphone size={18} className="text-cyan-400" />
                  {Number(a.price).toLocaleString()} {a.currency}
                </p>
                <p className="text-sm text-slate-400 mt-1 flex items-center gap-1">
                  <MapPin size={14} />
                  {routeLabel(a.waypoints)}
                </p>
                <span className="inline-block mt-2 text-xs rounded-full bg-slate-700 px-2 py-0.5 text-slate-300">
                  {a.status}
                </span>
              </div>
              <ChevronRight className="text-slate-500 shrink-0" />
            </div>
          </Link>
        ))
      )}

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Safar e'loni" wide>
        <form onSubmit={handleCreate} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400">Narx (UZS) *</label>
              <input
                type="number"
                className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-white"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Jo&apos;nash sanasi *</label>
              <input
                type="datetime-local"
                className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-white"
                value={departureDate}
                onChange={(e) => setDepartureDate(e.target.value)}
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400">Bo&apos;sh og&apos;irlik (t)</label>
              <input
                type="number"
                className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-white"
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-slate-400">Bo&apos;sh hajm (m³)</label>
              <input
                type="number"
                className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-white"
                value={volume}
                onChange={(e) => setVolume(e.target.value)}
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-slate-400">Tavsif</label>
            <textarea
              rows={2}
              className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-white"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-white">Marshrut nuqtalari</span>
              <button type="button" onClick={addWaypoint} className="text-xs text-cyan-400">
                + Nuqta
              </button>
            </div>
            {waypoints.map((wp, idx) => (
              <div key={idx} className="rounded-xl border border-slate-700 bg-slate-900/50 p-3 space-y-2">
                <div className="flex gap-2">
                  <select
                    className="flex-1 rounded-lg border border-slate-600 bg-slate-800 px-2 py-2 text-sm text-white"
                    value={wp.waypoint_type}
                    onChange={(e) =>
                      updateWp(idx, { waypoint_type: e.target.value as AnnouncementWaypointType })
                    }
                  >
                    <option value="origin">Boshlanish</option>
                    <option value="transit">Oraliq</option>
                    <option value="destination">Manzil</option>
                  </select>
                  {waypoints.length > 2 && (
                    <button type="button" onClick={() => removeWaypoint(idx)} className="text-rose-400 p-2">
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
                <input
                  placeholder="Shahar *"
                  className="w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-white text-sm"
                  value={wp.city}
                  onChange={(e) => updateWp(idx, { city: e.target.value })}
                />
              </div>
            ))}
          </div>

          <button
            type="submit"
            disabled={saving}
            className="w-full rounded-xl bg-gradient-to-r from-violet-600 to-cyan-500 py-3 font-semibold text-white disabled:opacity-50"
          >
            {saving ? "..." : "E'lonni joylash"}
          </button>
        </form>
      </Modal>
    </div>
  );
};
