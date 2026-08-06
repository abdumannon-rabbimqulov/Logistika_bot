import { useEffect, useState } from 'react';
import { ApiError } from '../api/client';
import { getPriceOptions, setCustomPrice } from '../api/orders';
import type { OrderDetail, OrderPriceOptionsResponse } from '../types/api';
import { formatPrice } from '../utils/format';
import { BottomSheetModal } from './BottomSheetModal';
import styles from './CustomPriceSheet.module.css';

// Sender narxni o'zi belgilaydi (PATCH /orders/{id}/price).
//
// Chegaralarni SERVER beradi (`GET /orders/{id}/price-options`) — frontend hisoblamaydi,
// aks holda bot va web turli chegaralarni ko'rsatardi. Oshirish cheklanmagan;
// pasaytirish esa admin sozlamasidagi chegirma foizi bilan cheklangan va chegaradan
// past narx serverda 400 bilan rad etiladi.

interface Props {
  order: OrderDetail;
  onClose: () => void;
  onSaved: (order: OrderDetail) => void;
}

export function CustomPriceSheet({ order, onClose, onSaved }: Props) {
  const [options, setOptions] = useState<OrderPriceOptionsResponse | null>(null);
  const [price, setPrice] = useState(String(order.price));
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getPriceOptions(order.id)
      .then((res) => !cancelled && setOptions(res))
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : 'Chegaralar yuklanmadi');
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [order.id]);

  const value = Number(price.replace(/\s/g, '').replace(',', '.'));
  const numeric = Number.isFinite(value) && value > 0;
  // Chegarani mahalliy tekshirish — foydalanuvchi 400 kutmasdan darhol ko'rsin.
  // Yakuniy qaror baribir serverda (services/pricing.py).
  const belowMin = options != null && numeric && value < options.min_allowed_price;
  const valid = numeric && !belowMin;

  async function save() {
    if (!valid || saving) return;
    setSaving(true);
    setError(null);
    try {
      onSaved(await setCustomPrice(order.id, value));
    } catch (err) {
      if (err instanceof ApiError) {
        // Qidiruv ketayotgani sababli rad etilgan bo'lsa backend kod bilan yuboradi
        // (`dispatch.ensure_price_editable`). `DISPATCH_OFFER_ACTIVE` da qolgan soniya
        // ham keladi — foydalanuvchi qancha kutishini bilib tursin.
        const locked = err.problems.find((p) => p.code === 'DISPATCH_OFFER_ACTIVE');
        const secondsLeft = typeof locked?.seconds_left === 'number' ? locked.seconds_left : null;
        setError(
          secondsLeft != null
            ? `${locked?.message} (~${secondsLeft} soniya qoldi)`
            : err.message,
        );
      } else {
        setError("Narxni o'zgartirib bo'lmadi");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <BottomSheetModal title="Narxni belgilash" onClose={onClose}>
      <div className={styles.form}>
        {error && <div className={styles.error}>{error}</div>}

        {loading ? (
          <div className={styles.skeleton} />
        ) : (
          <>
            {options && (
              <div className={styles.bounds}>
                <div className={styles.boundRow}>
                  <span>Hisoblangan narx</span>
                  <strong>{formatPrice(options.base_price)}</strong>
                </div>
                <div className={styles.boundRow}>
                  <span>Eng past ruxsat etilgan</span>
                  <strong>{formatPrice(options.min_allowed_price)}</strong>
                </div>
                <div className={styles.boundHint}>
                  Narxni oshirish cheklanmagan — yuqori narxda haydovchi tezroq topiladi.
                  Pasaytirish esa {options.max_discount_percent}% gacha.
                </div>
              </div>
            )}

            <label className={styles.field}>
              <span className={styles.label}>Yangi narx (UZS)</span>
              <input
                className={styles.input}
                inputMode="numeric"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
              />
            </label>

            {belowMin && options && (
              <div className={styles.invalid}>
                Narx {formatPrice(options.min_allowed_price)} dan past bo'lmasligi kerak
              </div>
            )}

            {options && options.quick_price_options.length > 0 && (
              <div className={styles.quick}>
                {options.quick_price_options.map((option) => (
                  <button
                    key={option.increment}
                    type="button"
                    className={styles.quickBtn}
                    onClick={() => setPrice(String(option.price))}
                  >
                    +{formatPrice(option.increment)}
                  </button>
                ))}
              </div>
            )}

            <button className={styles.submit} disabled={!valid || saving} onClick={save}>
              {saving ? 'Saqlanmoqda...' : 'Narxni saqlash'}
            </button>
          </>
        )}
      </div>
    </BottomSheetModal>
  );
}
