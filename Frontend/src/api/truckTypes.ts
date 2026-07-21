import { api } from './client';
import type { TruckType } from '../types/api';

export function listTruckTypes(): Promise<TruckType[]> {
  return api.get<TruckType[]>('/drivers/truck-types', undefined, true);
}
