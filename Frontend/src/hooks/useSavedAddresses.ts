import { useCallback, useEffect, useState } from 'react';

// Backendda saqlangan manzillar uchun model/endpoint yo'q (tekshirildi) — V1 shunchaki
// qurilmada (localStorage) saqlanadi. Kelajakda serverga ko'chirish mumkin.

export interface SavedAddress {
  id: string;
  label: string;
  address: string;
  latitude: number;
  longitude: number;
}

const STORAGE_KEY = 'yuk_saved_addresses';

function load(): SavedAddress[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SavedAddress[]) : [];
  } catch {
    return [];
  }
}

export function useSavedAddresses() {
  const [addresses, setAddresses] = useState<SavedAddress[]>(() => load());

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(addresses));
  }, [addresses]);

  const add = useCallback((entry: Omit<SavedAddress, 'id'>) => {
    setAddresses((prev) => [...prev, { ...entry, id: crypto.randomUUID() }]);
  }, []);

  const remove = useCallback((id: string) => {
    setAddresses((prev) => prev.filter((a) => a.id !== id));
  }, []);

  return { addresses, add, remove };
}
