// HomePage'dan OrderPage'ga (router state orqali) uzatiladigan oldindan to'ldirish ma'lumoti —
// "Takrorlash" yoki tezkor transport tanlashda ishlatiladi.

export interface OrderPointPrefill {
  address: string;
  latitude: number;
  longitude: number;
}

export interface OrderPrefillState {
  truckTypeId?: number;
  origin?: OrderPointPrefill;
  destination?: OrderPointPrefill;
}
