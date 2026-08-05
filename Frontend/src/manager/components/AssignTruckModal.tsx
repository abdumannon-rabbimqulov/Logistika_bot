import { useCallback, useEffect, useState } from 'react';
import { ApiError } from '../../api/client';
import { assignTruck, listAvailableTrucks } from '../../api/manager';
import { Modal } from '../../admin/components/Modal';
import shared from '../../admin/shared.module.css';
import type { AvailableTruck, ManagerOrderDetail } from '../../types/api';
import styles from './AssignTruckModal.module.css';

// Buyurtmaga mashina biriktirish. Alohida `trucks` jadvali yo'q — mashina haydovchi
// profilining bir qismi, shuning uchun serverga `driver_id` yuboriladi.
//
// Standart holatda faqat buyurtma talab qilgan turdagi, bo'sh va tasdiqlangan
// mashinalar ko'rsatiladi. `any_truck_type` — favqulodda holat uchun: mos mashina
// topilmaganda menejer boshqa turdagisini tanlashi mumkin.

interface Props {
  orderId: number;
  onClose: () => void;
  onAssigned: (order: ManagerOrderDetail) => void;
}

export function AssignTruckModal({ orderId, onClose, onAssigned }: Props) {
  const [trucks, setTrucks] = useState<AvailableTruck[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [onlyFree, setOnlyFree] = useState(true);
  const [anyType, setAnyType] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setTrucks(await listAvailableTrucks(orderId, { only_free: onlyFree, any_truck_type: anyType }));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Mashinalar yuklanmadi');
    } finally {
      setLoading(false);
    }
  }, [orderId, onlyFree, anyType]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit() {
    if (selected == null || saving) return;
    setSaving(true);
    setError(null);
    try {
      const result = await assignTruck(orderId, selected);
      onAssigned(result.order);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Biriktirib bo‘lmadi');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      title="Mashina biriktirish"
      onClose={onClose}
      footer={
        <div className={styles.footer}>
          <span className={styles.count}>{trucks.length} ta mashina</span>
          <div className={styles.footerBtns}>
            <button className={shared.ghostBtn} onClick={onClose}>
              Bekor qilish
            </button>
            <button
              className={shared.primaryBtn}
              disabled={selected == null || saving}
              onClick={submit}
            >
              {saving ? 'Biriktirilmoqda...' : 'Biriktirish'}
            </button>
          </div>
        </div>
      }
    >
      <div className={styles.body}>
        <div className={styles.filters}>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={onlyFree}
              onChange={(e) => {
                setOnlyFree(e.target.checked);
                setSelected(null);
              }}
            />
            <span>Faqat bo‘sh va tasdiqlangan</span>
          </label>
          <label className={styles.checkbox}>
            <input
              type="checkbox"
              checked={anyType}
              onChange={(e) => {
                setAnyType(e.target.checked);
                setSelected(null);
              }}
            />
            <span>Boshqa turdagi mashinalarni ham ko‘rsatish</span>
          </label>
        </div>

        {error && <div className={shared.errorBanner}>{error}</div>}

        {loading ? (
          <div className={styles.placeholder}>Yuklanmoqda...</div>
        ) : trucks.length === 0 ? (
          <div className={styles.placeholder}>
            Mos mashina topilmadi. Filtrlarni yumshatib ko‘ring.
          </div>
        ) : (
          <ul className={styles.list}>
            {trucks.map((truck) => (
              <li key={truck.driver_id}>
                <button
                  className={selected === truck.driver_id ? styles.itemActive : styles.item}
                  onClick={() => setSelected(truck.driver_id)}
                >
                  <div className={styles.itemHead}>
                    <span className={styles.plate}>{truck.truck_number}</span>
                    <span className={styles.typeName}>{truck.truck_type_name}</span>
                    {truck.is_blocked && <span className={styles.blocked}>Bloklangan</span>}
                    {!truck.is_available && <span className={styles.busy}>Band</span>}
                  </div>
                  <div className={styles.itemMeta}>
                    Haydovchi #{truck.driver_id} · Reyting {truck.rating} · {truck.total_trips} reys
                    {truck.max_weight != null && ` · ${truck.max_weight} t`}
                    {truck.truck_year != null && ` · ${truck.truck_year}-yil`}
                  </div>
                  {(truck.current_city || truck.current_region) && (
                    <div className={styles.itemLoc}>
                      {[truck.current_city, truck.current_region].filter(Boolean).join(', ')}
                    </div>
                  )}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Modal>
  );
}
