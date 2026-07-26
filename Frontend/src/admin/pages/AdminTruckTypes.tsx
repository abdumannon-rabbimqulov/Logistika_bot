import { useEffect, useState } from 'react';
import { ApiError } from '../../api/client';
import { deleteTruckType, listTruckTypes, staticFileUrl } from '../../api/truckTypes';
import type { TruckType } from '../../types/api';
import { formatPrice } from '../../utils/format';
import { DataTable, type Column } from '../components/DataTable';
import { Modal } from '../components/Modal';
import { TruckTypeFormModal } from '../components/TruckTypeFormModal';
import { EditIcon, PlusIconAdmin, TrashIcon } from '../icons';
import shared from '../shared.module.css';
import styles from './AdminTruckTypes.module.css';

/** Rasm ko'rsatkichi — URL yaroqsiz bo'lsa (masalan eski/qo'lda yozilgan qiymat)
 *  brauzerning "buzilgan rasm" ikonkasi o'rniga bo'sh joy ko'rsatiladi. */
function Thumb({ url }: { url: string | null }) {
  const [failed, setFailed] = useState(false);
  if (!url || failed) return <div className={styles.thumbEmpty} />;
  return <img className={styles.thumb} src={staticFileUrl(url)} alt="" onError={() => setFailed(true)} />;
}

export function AdminTruckTypes() {
  const [items, setItems] = useState<TruckType[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<TruckType | null>(null);
  const [deleting, setDeleting] = useState<TruckType | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  function load() {
    setError(null);
    listTruckTypes()
      .then(setItems)
      .catch((err) => {
        setError(err instanceof ApiError ? err.message : 'Yuklanmadi');
        setItems([]);
      });
  }

  useEffect(load, []);

  function openCreate() {
    setEditing(null);
    setFormOpen(true);
  }

  function openEdit(t: TruckType) {
    setEditing(t);
    setFormOpen(true);
  }

  async function confirmDelete() {
    if (!deleting) return;
    setDeleteBusy(true);
    try {
      await deleteTruckType(deleting.id);
      setDeleting(null);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "O'chirib bo'lmadi");
    } finally {
      setDeleteBusy(false);
    }
  }

  const columns: Column<TruckType>[] = [
    {
      key: 'name',
      header: 'Nomi',
      render: (t) => (
        <div className={styles.nameCell}>
          <Thumb url={t.image_url} />
          <div>
            <div className={styles.name}>{t.name}</div>
            {!t.is_active && <span className={styles.inactive}>Nofaol</span>}
          </div>
        </div>
      ),
    },
    {
      key: 'capacity',
      header: 'Sig‘im',
      render: (t) => `${t.max_weight} t · ${t.max_volume} m³`,
    },
    { key: 'base_price', header: "Boshlang'ich", align: 'right', render: (t) => formatPrice(Number(t.base_price)) },
    { key: 'price_per_km', header: '1 km', align: 'right', render: (t) => formatPrice(Number(t.price_per_km)) },
    {
      key: 'min_price',
      header: 'Minimal',
      align: 'right',
      render: (t) => (t.min_price != null ? formatPrice(Number(t.min_price)) : '—'),
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      width: '110px',
      render: (t) => (
        <div className={styles.actions}>
          <button className={styles.iconBtn} onClick={() => openEdit(t)} aria-label="Tahrirlash">
            <EditIcon />
          </button>
          <button className={styles.iconBtn} onClick={() => setDeleting(t)} aria-label="O'chirish">
            <TrashIcon />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className={shared.page}>
      <div className={shared.pageHead}>
        <div>
          <h1 className={shared.pageTitle}>Transport turlari</h1>
          <div className={shared.pageSub}>Buyurtma narxi shu tariflardan hisoblanadi</div>
        </div>
        <button className={shared.primaryBtn} onClick={openCreate}>
          <PlusIconAdmin /> Yangi tur
        </button>
      </div>

      {error && <div className={shared.errorBanner}>{error}</div>}

      <DataTable
        columns={columns}
        rows={items ?? []}
        rowKey={(t) => t.id}
        loading={items === null}
        emptyText="Hali transport turi qo'shilmagan"
      />

      {formOpen && (
        <TruckTypeFormModal
          editing={editing}
          onClose={() => setFormOpen(false)}
          onSaved={() => {
            setFormOpen(false);
            load();
          }}
        />
      )}

      {deleting && (
        <Modal
          title="O'chirishni tasdiqlang"
          onClose={() => setDeleting(null)}
          footer={
            <>
              <button className={styles.cancelBtn} onClick={() => setDeleting(null)} disabled={deleteBusy}>
                Bekor qilish
              </button>
              <button className={styles.deleteBtn} onClick={confirmDelete} disabled={deleteBusy}>
                {deleteBusy ? "O'chirilmoqda..." : "O'chirish"}
              </button>
            </>
          }
        >
          <div className={styles.confirmText}>
            <b>{deleting.name}</b> transport turini o'chirmoqchimisiz? Bu amalni ortga qaytarib bo'lmaydi.
          </div>
        </Modal>
      )}
    </div>
  );
}
