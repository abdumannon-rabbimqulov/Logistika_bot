import { api } from './client';
import type { TruckType, TruckTypeInput } from '../types/api';

export function listTruckTypes(): Promise<TruckType[]> {
  return api.get<TruckType[]>('/drivers/truck-types', undefined, true);
}

export function getTruckType(id: number): Promise<TruckType> {
  return api.get<TruckType>(`/drivers/truck-types/${id}`, undefined, true);
}

export function createTruckType(data: TruckTypeInput): Promise<TruckType> {
  return api.post<TruckType>('/drivers/truck-types', data);
}

export function updateTruckType(id: number, data: Partial<TruckTypeInput>): Promise<TruckType> {
  return api.patch<TruckType>(`/drivers/truck-types/${id}`, data);
}

export function deleteTruckType(id: number): Promise<void> {
  return api.delete<void>(`/drivers/truck-types/${id}`);
}
