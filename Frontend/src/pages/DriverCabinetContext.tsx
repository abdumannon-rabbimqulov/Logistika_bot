import { createContext, useContext } from 'react';
import type { DriverCabinet } from '../types/api';

export interface CabinetContextValue {
  cabinet: DriverCabinet;
  setCabinet: (cabinet: DriverCabinet) => void;
  reloadCabinet: () => Promise<void>;
}

export const CabinetContext = createContext<CabinetContextValue | null>(null);

/** Haydovchi kabineti holatini (balans, reyting, liniya statusi) barcha driver sahifalari
 *  bir manbadan o'qishi/yangilashi uchun kontekst — prop drilling'siz. */
export function useDriverCabinet(): CabinetContextValue {
  const ctx = useContext(CabinetContext);
  if (!ctx) throw new Error('useDriverCabinet DriverApp ichida ishlatilishi kerak');
  return ctx;
}
