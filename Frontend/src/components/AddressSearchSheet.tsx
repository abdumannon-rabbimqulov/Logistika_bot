import { useEffect, useRef, useState } from 'react';
import { searchAddress } from '../api/orders';
import type { GeocodeSuggestion } from '../types/api';
import { BottomSheetModal } from './BottomSheetModal';
import styles from './AddressSearchSheet.module.css';
import { SearchIcon } from './icons';

interface Props {
  title: string;
  onSelect: (suggestion: GeocodeSuggestion) => void;
  onClose: () => void;
}

export function AddressSearchSheet({ title, onSelect, onClose }: Props) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<GeocodeSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (query.trim().length < 3) {
      setResults([]);
      return;
    }
    setLoading(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await searchAddress(query.trim());
        setResults(res);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 350);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  return (
    <BottomSheetModal title={title} onClose={onClose}>
      <input
        ref={inputRef}
        className={styles.input}
        placeholder="Manzilni kiriting..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      {query.trim().length < 3 && <div className={styles.hint}>Kamida 3 ta harf kiriting</div>}
      {loading && <div className={styles.hint}>Qidirilmoqda...</div>}
      {!loading && query.trim().length >= 3 && results.length === 0 && (
        <div className={styles.hint}>Hech narsa topilmadi</div>
      )}
      <div className={styles.list}>
        {results.map((r, i) => (
          <button key={`${r.latitude}-${r.longitude}-${i}`} className={styles.item} onClick={() => onSelect(r)}>
            <SearchIcon />
            <span className={styles.itemText}>{r.address}</span>
          </button>
        ))}
      </div>
    </BottomSheetModal>
  );
}
