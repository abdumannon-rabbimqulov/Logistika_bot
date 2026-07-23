from __future__ import annotations

import asyncio
import logging
from decimal import Decimal
from typing import Optional, Sequence

from geoalchemy2.elements import WKTElement
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from driver.models import TruckType
from order.models import Order, OrderRoutePostGIS, OrderStatus, OrderWaypoint
from order.schemas import OrderCreate, PriceEstimateRequest, OrderUpdate, OrderWaypointCreate
from services import billing, osrm_client, yandex_geocoder
from utils.geo import simplify_polyline

logger = logging.getLogger(__name__)


def _overload_warning(data: OrderCreate, truck_type: TruckType) -> Optional[str]:
    """Yuk og'irligi/hajmi tanlangan mashina sig'imidan oshsa ogohlantirish matni qaytaradi.

    Majburiy taqiq YO'Q — O'zbekiston bozorida haydovchilar ko'pincha e'lon qilingan
    sig'imdan ortiqni ham qabul qiladi. Faqat ko'rinadigan ogohlantirish beriladi.
    """
    parts: list[str] = []
    if data.weight is not None and data.weight > truck_type.max_weight:
        parts.append(f"og'irlik {data.weight}t > {truck_type.max_weight}t")
    if data.volume is not None and truck_type.max_volume is not None and data.volume > truck_type.max_volume:
        parts.append(f"hajm {data.volume}m³ > {truck_type.max_volume}m³")
    if not parts:
        return None
    return "Tanlangan mashina (" + truck_type.name + ") sig'imidan oshadi: " + ", ".join(parts)


async def _resolve_location(
    address: Optional[str], latitude: Optional[Decimal], longitude: Optional[Decimal]
) -> tuple[Optional[str], float, float]:
    """(address, latitude, longitude) — yetishmagan tomonini to'ldiradi.

    - Koordinata berilgan bo'lsa (masalan sender Telegram orqali o'z joylashuvini yuborgan) —
      koordinata ustuvor, manzil matni bo'lmasa reverse-geocoding bilan topiladi.
    - Faqat manzil matni berilgan bo'lsa — Yandex Geocoder orqali qidirilib, eng mos
      (birinchi) natijaning koordinatasi olinadi.
    """
    if latitude is not None and longitude is not None:
        lat, lon = float(latitude), float(longitude)
        if not address:
            address = await yandex_geocoder.reverse_geocode(lat, lon)
        return address, lat, lon

    candidates = await yandex_geocoder.search_address(address or "")
    if not candidates:
        raise ValueError(f"Manzil topilmadi: '{address}'")
    best = candidates[0]
    return best.address, best.latitude, best.longitude


async def _resolve_waypoint_location(wp: OrderWaypointCreate) -> tuple[Optional[str], float, float]:
    return await _resolve_location(wp.address, wp.latitude, wp.longitude)


async def create_order(db: AsyncSession, data: OrderCreate, *, customer_id: int) -> Order:
    truck_type = await db.get(TruckType, data.required_truck_type_id)
    if not truck_type or not truck_type.is_active:
        raise ValueError("Ko'rsatilgan mashina turi topilmadi yoki faol emas")

    # Har bir waypoint mustaqil ravishda geocode qilinadi — ketma-ket kutish o'rniga
    # parallel yuborish umumiy javob vaqtini (N ta manzil bo'lsa ham) bitta so'rovga tenglashtiradi.
    resolved: list[tuple[Optional[str], float, float]] = list(
        await asyncio.gather(*(_resolve_waypoint_location(wp) for wp in data.waypoints))
    )

    # Narx masofaga bog'liq bo'lgani uchun marshrutsiz buyurtma yaratib bo'lmaydi —
    # avval mijozdan qo'lda qabul qilingan `price` shu yerda ishonchsiz manba edi.
    try:
        route = await osrm_client.get_route([(lat, lon) for _, lat, lon in resolved])
    except osrm_client.OSRMNoRouteError as exc:
        # Nuqtalar yo'ldan uzoq — mijoz boshqa manzil tanlashi kerak (422).
        # OSRMUnavailableError esa ushlanmaydi: u infratuzilma nosozligi, router 503 qaytaradi.
        raise ValueError(f"Bu manzillar orasida yo'l topilmadi, buyurtma yaratilmadi: {exc}") from exc

    distance_km = Decimal(str(route.distance_km))
    price = truck_type.calculate_price(distance_km)

    order = Order(
        customer_id=customer_id,
        cargo_name=data.cargo_name,
        weight=data.weight,
        volume=data.volume,
        pickup_at=data.pickup_at,
        required_truck_type_id=data.required_truck_type_id,
        price=price,
        currency="UZS",
        total_distance_km=distance_km,
        overload_warning=_overload_warning(data, truck_type),
        route=OrderRoutePostGIS(geom_route=WKTElement(route.geometry_wkt, srid=4326)),
        waypoints=[
            OrderWaypoint(
                sequence=wp.sequence,
                type=wp.type,
                address=address,
                latitude=Decimal(str(lat)),
                longitude=Decimal(str(lon)),
                contact_name=wp.contact_name,
                contact_phone=wp.contact_phone,
            )
            for wp, (address, lat, lon) in zip(data.waypoints, resolved)
        ],
    )

    db.add(order)
    await db.commit()
    await db.refresh(order, attribute_names=["waypoints", "route"])

    # Avtomatik dispatch: eng yaqin/mos haydovchiga taklif yuborishni boshlaydi
    # (docs/DISPATCH_SYSTEM_PLAN.md). Bu xatoga uchrasa ham order yaratilishi buzilmasin —
    # order PENDING holatda qoladi, admin/keyingi sweep qayta urinib ko'radi.
    from services import dispatch as dispatch_service

    try:
        await dispatch_service.start_dispatch(db, order)
    except Exception:
        logger.exception("Order #%s uchun dispatch boshlanmadi", order.id)
        await db.rollback()

    return order


async def get_order(db: AsyncSession, order_id: int) -> Optional[Order]:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.waypoints), selectinload(Order.route))
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def list_orders_by_customer(db: AsyncSession, customer_id: int) -> Sequence[Order]:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.waypoints))
        .where(Order.customer_id == customer_id)
        .order_by(Order.created_at.desc())
    )
    return result.scalars().all()


async def list_orders_by_driver(db: AsyncSession, driver_id: int) -> Sequence[Order]:
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.waypoints))
        .where(Order.driver_id == driver_id)
        .order_by(Order.created_at.desc())
    )
    return result.scalars().all()


async def list_available_orders(db: AsyncSession, *, truck_type_id: Optional[int] = None) -> Sequence[Order]:
    """Hali haydovchisi biriktirilmagan, PENDING holatdagi buyurtmalar (haydovchi ilovasi uchun)."""
    query = (
        select(Order)
        .options(selectinload(Order.waypoints))
        .where(Order.status == OrderStatus.PENDING, Order.driver_id.is_(None))
        .order_by(Order.created_at.desc())
    )
    if truck_type_id is not None:
        query = query.where(Order.required_truck_type_id == truck_type_id)
    result = await db.execute(query)
    return result.scalars().all()


async def update_order(db: AsyncSession, order: Order, data: OrderUpdate) -> Order:
    values = data.model_dump(exclude_unset=True)
    if values:
        await db.execute(update(Order).where(Order.id == order.id).values(**values))
        await db.commit()
        await db.refresh(order, attribute_names=[*values.keys(), "updated_at"])
    return order


async def update_order_status(db: AsyncSession, order: Order, new_status: OrderStatus) -> Order:
    was_completed = order.status == OrderStatus.COMPLETED
    order.status = new_status
    await db.commit()
    await db.refresh(order, attribute_names=["status", "updated_at"])

    # Komissiya faqat PENDING/ACCEPTED/IN_PROGRESS -> COMPLETED o'tishida bir marta yechiladi
    # (allaqachon COMPLETED bo'lgan orderni qayta COMPLETED qilish qayta hisoblamaydi).
    if new_status == OrderStatus.COMPLETED and not was_completed:
        try:
            await billing.charge_order_commission(db, order)
        except Exception as exc:
            logger.exception("Order #%s uchun komissiya yechishda xato", order.id)
            # Xato jim qolmasin — komissiya yechilmasa tizim pul yo'qotadi, admin darhol
            # Telegram orqali xabardor bo'lishi kerak (order baribir COMPLETED holatda qoladi).
            from utils.admin_alerts import format_details_for_alert, send_error_to_admins

            await send_error_to_admins(
                title="Komissiya yechishda xato",
                request_id="-",
                method="INTERNAL",
                path=f"order/{order.id}/complete",
                client="-",
                exc_type=type(exc).__name__,
                details=format_details_for_alert(exc),
            )

    return order


async def assign_driver(db: AsyncSession, order: Order, driver_id: int) -> Optional[Order]:
    """Haydovchini biriktiradi — atomik (`WHERE driver_id IS NULL`), shuning uchun bir
    vaqtda kelgan ikkinchi so'rov 0 qator yangilaydi va `None` qaytaradi (409 uchun)."""
    result = await db.execute(
        update(Order)
        .where(Order.id == order.id, Order.driver_id.is_(None))
        .values(driver_id=driver_id, status=OrderStatus.ACCEPTED)
    )
    if result.rowcount == 0:
        await db.rollback()
        return None
    await db.commit()
    await db.refresh(order, attribute_names=["driver_id", "status", "updated_at"])
    return order


async def delete_order(db: AsyncSession, order: Order) -> None:
    await db.delete(order)
    await db.commit()


async def estimate_price(db: AsyncSession, data: PriceEstimateRequest) -> dict:
    """Pickup/delivery manzillari bo'yicha masofani hisoblab, barcha aktiv mashina
    turlari uchun narxni qaytaradi (mijoz mashina tanlashdan oldin ko'radi)."""
    (origin_address, origin_lat, origin_lon), (dest_address, dest_lat, dest_lon) = await asyncio.gather(
        _resolve_location(data.origin.address, data.origin.latitude, data.origin.longitude),
        _resolve_location(data.destination.address, data.destination.latitude, data.destination.longitude),
    )

    try:
        route = await osrm_client.get_route([(origin_lat, origin_lon), (dest_lat, dest_lon)])
    except osrm_client.OSRMNoRouteError as exc:
        raise ValueError(f"Bu manzillar orasida yo'l topilmadi: {exc}") from exc

    distance_km = Decimal(str(route.distance_km))

    result = await db.execute(select(TruckType).where(TruckType.is_active.is_(True)))
    truck_types = result.scalars().all()

    options = sorted(
        (
            {
                "truck_type_id": tt.id,
                "name": tt.name,
                "image_url": tt.image_url,
                "price": tt.calculate_price(distance_km),
            }
            for tt in truck_types
        ),
        key=lambda o: o["price"],
    )

    return {
        "origin_address": origin_address,
        "origin_latitude": origin_lat,
        "origin_longitude": origin_lon,
        "destination_address": dest_address,
        "destination_latitude": dest_lat,
        "destination_longitude": dest_lon,
        "distance_km": distance_km,
        "duration_min": Decimal(str(route.duration_min)),
        # To'liq geometriya bazaga saqlanadigan aniqlikda — xaritada ko'rsatish uchun
        # shuncha nuqta shart emas, shuning uchun javob hajmi soddalashtirib kichraytiriladi.
        "route_geometry": simplify_polyline(route.geometry),
        "options": options,
    }
