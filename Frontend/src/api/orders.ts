import { api } from './client';
import type {
  GeocodeSuggestion,
  OrderCreateInput,
  OrderDetail,
  OrderListItem,
  PriceEstimateLocation,
  PriceEstimateResponse,
  ReverseGeocodeResponse,
} from '../types/api';

export function createOrder(data: OrderCreateInput): Promise<OrderDetail> {
  return api.post<OrderDetail>('/orders', data);
}

export function listMyOrders(): Promise<OrderListItem[]> {
  return api.get<OrderListItem[]>('/orders');
}

export function getOrder(orderId: number): Promise<OrderDetail> {
  return api.get<OrderDetail>(`/orders/${orderId}`);
}

export function searchAddress(query: string): Promise<GeocodeSuggestion[]> {
  return api.get<GeocodeSuggestion[]>('/orders/geocode/search', { q: query });
}

export function reverseGeocode(latitude: number, longitude: number): Promise<ReverseGeocodeResponse> {
  return api.get<ReverseGeocodeResponse>('/orders/geocode/reverse', { latitude, longitude });
}

export function estimatePrice(
  origin: PriceEstimateLocation,
  destination: PriceEstimateLocation,
): Promise<PriceEstimateResponse> {
  return api.post<PriceEstimateResponse>('/orders/estimate-price', { origin, destination });
}

export function bumpPrice(orderId: number, price: number): Promise<OrderDetail> {
  return api.post<OrderDetail>(`/orders/${orderId}/price-bump`, { price });
}
