import { ChevronRightIcon, DocIcon, ShieldIcon, StarIcon, UserLineIcon } from '../components/icons';
import { DriverBottomNav } from '../components/DriverBottomNav';
import { useDriverCabinet } from './DriverCabinetContext';
import styles from './DriverProfilePage.module.css';

export function DriverProfilePage() {
  const { cabinet } = useDriverCabinet();
  const reliability = Math.round(cabinet.on_time_percent);
  const initials = cabinet.name?.trim().charAt(0).toUpperCase() || 'H';

  return (
    <div className={styles.page}>
      <div className={styles.scroll}>
        <div className={styles.title}>Profil</div>

        {/* Bosh karta: avatar, ism, reyting */}
        <div className={styles.headerCard}>
          <div className={styles.avatar}>{initials}</div>
          <div className={styles.headerInfo}>
            <div className={styles.name}>{cabinet.name}</div>
            <div className={styles.ratingRow}>
              <StarIcon size={14} /> {cabinet.rating.toFixed(1)}
              <span className={styles.trips}>· {cabinet.total_trips} safar</span>
            </div>
          </div>
        </div>

        {/* Mashina kartasi */}
        <div className={styles.sectionTitle}>Transport</div>
        <div className={styles.truckCard}>
          <div className={styles.truckRow}>
            <span className={styles.truckLabel}>Turi</span>
            <span className={styles.truckValue}>{cabinet.truck_type_name ?? '—'}</span>
          </div>
          <div className={styles.truckRow}>
            <span className={styles.truckLabel}>Davlat raqami</span>
            <span className={styles.truckValue}>{cabinet.truck_number}</span>
          </div>
          <div className={styles.truckRow}>
            <span className={styles.truckLabel}>Ishlab chiqarilgan yili</span>
            <span className={styles.truckValue}>{cabinet.truck_year ?? '—'}</span>
          </div>
        </div>

        {/* Ishonchlilik balli */}
        <div className={styles.reliabilityCard}>
          <div className={styles.reliabilityHead}>
            <span className={styles.reliabilityTitle}>
              <ShieldIcon size={17} /> Ishonchlilik balli
            </span>
            <span className={styles.reliabilityValue}>{reliability}%</span>
          </div>
          <div className={styles.progressTrack}>
            <div className={styles.progressFill} style={{ width: `${Math.min(100, reliability)}%` }} />
          </div>
          <div className={styles.reliabilityHint}>
            Vaqtida yetkazish {reliability}% · yuqori ball ko'proq buyurtma olishga yordam beradi.
          </div>
        </div>

        {/* Qatorlar (keyingi bosqich uchun) */}
        <div className={styles.rows}>
          <button className={styles.row}>
            <span className={styles.rowIcon}><DocIcon /></span>
            <span className={styles.rowText}>
              <span className={styles.rowTitle}>Hujjatlar</span>
              <span className={styles.rowSub}>Prava, texpasport, sug'urta</span>
            </span>
            <ChevronRightIcon />
          </button>
          <button className={styles.row}>
            <span className={styles.rowIcon}><UserLineIcon /></span>
            <span className={styles.rowText}>
              <span className={styles.rowTitle}>Shaxsiy ma'lumotlar</span>
              <span className={styles.rowSub}>{cabinet.phone_number ?? 'Telefon qo’shilmagan'}</span>
            </span>
            <ChevronRightIcon />
          </button>
        </div>

        <div className={styles.note}>Hujjatlar va shaxsiy ma'lumotlarni tahrirlash tez orada qo'shiladi.</div>
      </div>

      <DriverBottomNav />
    </div>
  );
}
