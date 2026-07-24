import { useEffect, useState } from 'react';
import { getMyDriverCabinetOrNull } from '../api/drivers';
import type { DriverCabinet } from '../types/api';
import styles from '../App.module.css';
import { DriverApp } from './DriverApp';
import { DriverProfileSetupPage } from './DriverProfileSetupPage';

/** role === 'driver' bo'lganda: profil hali yo'q bo'lsa setup forma, bo'lsa kabinet. */
export function DriverGate() {
  const [cabinet, setCabinet] = useState<DriverCabinet | null | 'loading'>('loading');

  useEffect(() => {
    void load();
  }, []);

  async function load() {
    setCabinet('loading');
    try {
      const result = await getMyDriverCabinetOrNull();
      setCabinet(result);
    } catch {
      setCabinet(null);
    }
  }

  if (cabinet === 'loading') {
    return (
      <div className={styles.centerScreen}>
        <div className={styles.spinner} />
      </div>
    );
  }

  if (cabinet === null) {
    return <DriverProfileSetupPage onCreated={load} />;
  }

  return <DriverApp initialCabinet={cabinet} />;
}
