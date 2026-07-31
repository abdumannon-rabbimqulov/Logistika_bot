from __future__ import annotations

import asyncio
import json
import logging
from typing import List, NoReturn, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.config import ADMIN_IDS, async_session, get_db
from driver.crud import get_driver, get_driver_by_user_id
from users.crud import get_user_by_id
from order import crud, schemas
from order.models import Order, OrderStatus, WaypointStatus
from services import dispatch as dispatch_service
from services import geofence, live_location, notifications, order_flow, osrm_client, pricing, yandex_geocoder
from services.problems import WaypointProblem
from users.auth import get_current_active_user, get_current_sender, verify_token
from users.models import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["Buyurtmalar (Orders)"])


def _routing_unavailable() -> HTTPException:
    """OSRM ishlamayotganda qaytariladigan javob.

    503 (422 emas), chunki bu mijozning xatosi emas — u manzilni o'zgartirib qayta
    urinsa ham natija bo'lmaydi. Xatoning ichki matni (OSRM manzili, httpx tafsilotlari)
    mijozga berilmaydi — u faqat logga yoziladi (services/osrm_client.py).
    """
    return HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Marshrut xizmati vaqtincha ishlamayapti, biroz kutib qayta urinib ko'ring",
    )


def _raise_dispatch_error(exc: dispatch_service.DispatchError) -> NoReturn:
    raise HTTPException(exc.status_code, detail=str(exc)) from exc


def _is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN or user.id in ADMIN_IDS


async def _require_order_access(db: AsyncSession, order_id: int, current_user: User) -> Order:
    """Buyurtmani topadi va faqat egasi/biriktirilgan haydovchi/admin ko'ra olishini tekshiradi."""
    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Buyurtma topilmadi")

    if _is_admin(current_user) or order.customer_id == current_user.id:
        return order

    driver = await get_driver_by_user_id(db, current_user.id)
    if driver and order.driver_id == driver.id:
        return order

    raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Bu buyurtmaga kirish huquqingiz yo'q")


@router.post("", response_model=schemas.OrderDetailResponse, status_code=status.HTTP_201_CREATED,
             summary="Yangi buyurtma yaratish (sender)")
async def create_order(
    data: schemas.OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_sender),
):
    try:
        order = await crud.create_order(db, data, customer_id=current_user.id)
    except osrm_client.OSRMUnavailableError as exc:
        raise _routing_unavailable() from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    return schemas.OrderDetailResponse.from_order(order)


@router.get("", response_model=List[schemas.OrderListItem], summary="Mening buyurtmalarim")
async def list_my_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role == UserRole.DRIVER:
        driver = await get_driver_by_user_id(db, current_user.id)
        if not driver:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Haydovchi profili topilmadi")
        return await crud.list_orders_by_driver(db, driver.id)
    return await crud.list_orders_by_customer(db, current_user.id)


@router.get("/available/list", response_model=List[schemas.OrderListItem],
            summary="Haydovchisi topilmagan buyurtmalar (haydovchi uchun)")
async def list_available_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    truck_type_id: Optional[int] = Query(None),
):
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Bu ro'yxat faqat haydovchilar uchun")
    return await crud.list_available_orders(db, truck_type_id=truck_type_id)


@router.get("/geocode/search", response_model=List[schemas.GeocodeSuggestion],
            summary="Manzil qidirish (Yandex Geocoder, autocomplete)")
async def search_address(
    q: str = Query(..., min_length=3, description="Qidirilayotgan manzil matni"),
    _: User = Depends(get_current_active_user),
):
    results = await yandex_geocoder.search_address(q)
    return [
        schemas.GeocodeSuggestion(address=r.address, latitude=r.latitude, longitude=r.longitude)
        for r in results
    ]


@router.get("/geocode/reverse", response_model=schemas.ReverseGeocodeResponse,
            summary="Koordinata bo'yicha manzilni aniqlash (sender o'z joylashuvini yuborganda)")
async def reverse_geocode(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    _: User = Depends(get_current_active_user),
):
    address = await yandex_geocoder.reverse_geocode(latitude, longitude)
    return schemas.ReverseGeocodeResponse(address=address, latitude=latitude, longitude=longitude)


@router.post("/estimate-price", response_model=schemas.PriceEstimateResponse,
             summary="Manzillar bo'yicha barcha mashina turlari uchun narx taklifi")
async def estimate_price(
    data: schemas.PriceEstimateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    try:
        return await crud.estimate_price(db, data)
    except osrm_client.OSRMUnavailableError as exc:
        raise _routing_unavailable() from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{order_id}", response_model=schemas.OrderDetailResponse, summary="Buyurtma tafsilotlari")
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = await _require_order_access(db, order_id, current_user)
    return schemas.OrderDetailResponse.from_order(order)


@router.get(
    "/{order_id}/driver-location",
    response_model=schemas.OrderDriverLocationResponse,
    summary="Biriktirilgan haydovchining joriy jonli joylashuvi (sender/admin kuzatuvi uchun)",
)
async def get_order_driver_location(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Sender o'z buyurtmasini kuzatib borishi uchun — admin jonli xaritasidagi bilan
    bir xil manba (`services/live_location.py`), lekin faqat SHU buyurtmaga
    biriktirilgan haydovchi bo'yicha va faqat buyurtma egasi/haydovchi/admin ko'ra oladi
    (`_require_order_access`).
    """
    order = await _require_order_access(db, order_id, current_user)
    if order.driver_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Buyurtmaga hali haydovchi biriktirilmagan")

    item = await live_location.get_driver_location(order.driver_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Haydovchining jonli joylashuvi hozircha yo'q")
    return item


async def _resolve_order_track_ws_user(token: Optional[str]) -> Optional[User]:
    """WS `accept()`dan oldingi token tekshiruvi — driver/router.py naqshi bilan bir xil."""
    if not token:
        return None
    payload = verify_token(token)
    if not payload or payload.get("type") != "access":
        return None
    user_id = payload.get("sub")
    if not user_id:
        return None
    async with async_session() as db:
        return await get_user_by_id(db, int(user_id))


@router.websocket("/{order_id}/ws/driver-location")
async def order_driver_location_ws(
    websocket: WebSocket,
    order_id: int,
    token: Optional[str] = None,
):
    """Sender WebApp'ida jonli xarita uchun — buyurtmaga biriktirilgan haydovchining
    koordinatasi o'zgarganda darhol yuboriladi (admin `driver_locations_ws` bilan bir xil
    pub/sub manbadan, lekin faqat shu buyurtmaning haydovchisi bo'yicha filtrlanadi).
    """
    user = await _resolve_order_track_ws_user(token)
    if user is None:
        await websocket.close(code=4401)
        return

    async with async_session() as db:
        order = await crud.get_order(db, order_id)
        if order is None:
            await websocket.close(code=4404)
            return
        is_allowed = (
            _is_admin(user)
            or order.customer_id == user.id
            or (order.driver_id is not None and await _is_order_driver_user(db, order, user))
        )
        if not is_allowed:
            await websocket.close(code=4403)
            return
        driver_id = order.driver_id

    if driver_id is None:
        await websocket.accept()
        await websocket.send_text(json.dumps({"event": "no_driver"}))
        await websocket.close(code=4404)
        return

    await websocket.accept()

    try:
        snapshot = await live_location.get_driver_location(driver_id)
        await websocket.send_text(json.dumps({"event": "snapshot", "item": snapshot}))
    except Exception:
        logger.warning("order driver-location ws: snapshot yuborilmadi (order %s)", order_id)

    sub_task = asyncio.create_task(_pump_order_driver_updates(websocket, driver_id))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.debug("order driver-location ws receive xatosi: %s", exc)
    finally:
        sub_task.cancel()


async def _is_order_driver_user(db: AsyncSession, order: Order, user: User) -> bool:
    driver = await get_driver_by_user_id(db, user.id)
    return bool(driver and order.driver_id == driver.id)


async def _pump_order_driver_updates(websocket: WebSocket, driver_id: int) -> None:
    try:
        async for payload in live_location.subscribe_location_updates():
            if payload.get("driver_id") != driver_id:
                continue
            try:
                await websocket.send_text(json.dumps({"event": "update", "item": payload}))
            except Exception:
                break
    except asyncio.CancelledError:
        pass


@router.patch("/{order_id}", response_model=schemas.OrderDetailResponse, summary="Buyurtmani tahrirlash (egasi)")
async def update_order(
    order_id: int,
    data: schemas.OrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order = await _require_order_access(db, order_id, current_user)
    if not _is_admin(current_user) and order.customer_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Faqat buyurtma egasi tahrirlay oladi")
    order = await crud.update_order(db, order, data)
    return schemas.OrderDetailResponse.from_order(order)


@router.patch("/{order_id}/status", response_model=schemas.OrderResponse,
              summary="Buyurtma holatini qo'lda yangilash (faqat admin)")
async def update_order_status(
    order_id: int,
    data: schemas.OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """DIQQAT: bu endpoint endi FAQAT admin uchun.

    Ilgari biriktirilgan haydovchi ham statusni to'g'ridan-to'g'ri qo'ya olardi va shu
    yo'l bilan manzilga umuman bormasdan buyurtmani `COMPLETED` qilib, komissiyani
    ishga tushirardi. Endi haydovchi oqimni faqat nuqtalar orqali suradi
    (`PATCH /orders/{id}/waypoints/{waypoint_id}`), u yerda esa har qadam GPS bilan
    tekshiriladi — geofence'ni chetlab o'tadigan yo'l qolmasligi uchun.
    """
    order = await _require_order_access(db, order_id, current_user)

    if not _is_admin(current_user):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=(
                "Buyurtma holatini qo'lda faqat admin o'zgartira oladi. "
                "Haydovchi buyurtmani marshrut nuqtalari orqali yuritadi."
            ),
        )

    # `OrderFlowError` bu yerda ATAYLAB tutilmaydi — uni global handler 400 Bad Request
    # qilib qaytaradi (`middlewares/error_handler.py`). Shu bilan barcha endpointlarda
    # bir xil javob bo'ladi va yangi chaqiruv joyi qo'shilganda 500 berish xavfi yo'q.
    return await crud.update_order_status(db, order, data.status)


@router.patch("/{order_id}/waypoints/{waypoint_id}", response_model=schemas.OrderDetailResponse,
              summary="Marshrut nuqtasidagi qadamni belgilash (biriktirilgan haydovchi yoki admin)")
async def update_order_waypoint(
    order_id: int,
    waypoint_id: int,
    data: schemas.WaypointProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Haydovchi "Yetib keldim" / "Yukni ortdim" / "Yukni topshirdim" qadamlarini shu yerda belgilaydi.

    Har bir qadamda haydovchi nuqta atrofidagi radiusda ekani tekshiriladi
    (`services/geofence.py`). Buyurtma holati nuqtalardan kelib chiqib avtomatik
    yangilanadi: birinchi yuk ortish nuqtasi yopilsa `IN_PROGRESS`, oxirgisi yopilsa
    `COMPLETED` (va shu yerda komissiya yechiladi).
    """
    order = await _require_order_access(db, order_id, current_user)

    is_admin = _is_admin(current_user)
    is_assigned_driver = False
    if current_user.role == UserRole.DRIVER:
        driver = await get_driver_by_user_id(db, current_user.id)
        is_assigned_driver = bool(driver and order.driver_id == driver.id)

    if not is_admin and not is_assigned_driver:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Marshrut nuqtasini faqat biriktirilgan haydovchi yoki admin belgilay oladi",
        )

    waypoint = next((wp for wp in order.waypoints if wp.id == waypoint_id), None)
    if waypoint is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Bu buyurtmada bunday nuqta yo'q")

    # Qo'lda tasdiqlash (geofence'ni chetlab o'tish) va nuqtani tashlab ketish — faqat admin.
    override_reason = data.override_reason if is_admin else None
    if data.override_reason and not is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Qadamni qo'lda tasdiqlashni faqat administrator bajara oladi",
        )
    if data.status == WaypointStatus.SKIPPED and not is_admin:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Nuqtani tashlab ketishni faqat administrator belgilay oladi",
        )

    # Koordinata darhol yiqilmaydigan usulda olinadi: joylashuv aniqlanmagani ham
    # boshqa sabablar bilan BIRGA qaytishi kerak, ularni to'sib qo'ymasligi emas.
    coords = None
    coords_violation = None
    if not override_reason and data.status != WaypointStatus.SKIPPED:
        coords, coords_violation = await geofence.try_resolve_driver_coords(
            order.driver_id, data.latitude, data.longitude, data.accuracy
        )

    try:
        order = await order_flow.apply_waypoint_progress(
            db, order, waypoint, data.status,
            coords=coords,
            coords_violation=coords_violation,
            override_by_user_id=current_user.id if override_reason else None,
            override_reason=override_reason,
        )
    except WaypointProblem as exc:
        # Strukturali 422: barcha sabablar bir javobda, har biri kodi va aniq
        # raqamlari bilan (masofa, ruxsat etilgan radius, kutilayotgan nuqta ID si).
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail=exc.as_detail()
        ) from exc
    except geofence.GeofenceError as exc:
        # Zaxira: geofence bitta sabab bilan yiqilgan yo'l (matn `detail` bo'lib qaytadi).
        # `OrderFlowError` bu yerda tutilmaydi — global handler uni 400 qiladi.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return schemas.OrderDetailResponse.from_order(order)


@router.post("/{order_id}/assign-driver", response_model=schemas.OrderAssignDriverResponse,
             summary="Buyurtmaga qo'lda haydovchi biriktirish (faqat admin — favqulodda holat)")
async def assign_driver_to_order(
    order_id: int,
    data: schemas.OrderAssignDriver,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Buyurtma topilmasa yoki haydovchi topilmasa — 404; allaqachon biriktirilgan yoki
    haydovchi bloklangan bo'lsa — 409. Muvaffaqiyatda yangilangan buyurtma va haydovchi
    holati qaytadi (admin panel javobni to'g'ridan-to'g'ri ko'rsatadi).

    Oddiy oqimda haydovchi buyurtmani `POST /orders/dispatch/{attempt_id}/accept` orqali,
    navbat bilan kelgan taklifni qabul qilib oladi (services/dispatch.py). Bu endpoint
    faqat admin uchun — masalan avtomatik dispatch ishlamay qolgan holatlarda qo'lda
    tuzatish uchun. Avval driverlar bu yerdan o'zini to'g'ridan-to'g'ri biriktira olardi —
    bu ochiq ro'yxatda lock yo'q edi va poyga sharoitiga (race condition) olib kelardi.
    """
    if not _is_admin(current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Ruxsat yo'q")

    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Buyurtma topilmadi")

    driver = await get_driver(db, data.driver_id)
    if not driver:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Haydovchi topilmadi (id={data.driver_id})")

    driver_user = await get_user_by_id(db, driver.user_id)

    try:
        # Bekor qilish/bildirishnomalar `accept_attempt` bilan bir xil bo'lishi uchun
        # dispatch xizmatida (services/dispatch.py) — bu yerda takrorlanmaydi.
        await dispatch_service.assign_driver_manually(db, order, driver)
    except dispatch_service.DispatchError as exc:
        _raise_dispatch_error(exc)

    # `waypoints`/`route` bilan qayta yuklaymiz — javob sinxron serializatsiya qilinadi.
    refreshed = await crud.get_order(db, order_id) or order
    return schemas.OrderAssignDriverResponse(
        order=schemas.OrderDetailResponse.from_order(refreshed),
        driver=schemas.AssignedDriverInfo(
            driver_id=driver.id,
            user_id=driver.user_id,
            full_name=driver_user.full_name if driver_user else None,
            phone_number=driver_user.phone_number if driver_user else None,
            truck_number=driver.truck_number,
            truck_type_id=driver.truck_type_id,
            is_available=driver.is_available,
            is_blocked=driver.is_blocked,
            verification_status=driver.verification_status.value,
            rating=driver.rating,
            total_trips=driver.total_trips,
        ),
    )


@router.get("/dispatch/active", response_model=Optional[schemas.DispatchAttemptResponse],
            summary="Haydovchining joriy faol dispatch taklifi (WebApp sinxronlash uchun)")
async def get_active_dispatch(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Faqat haydovchilar uchun")
    driver = await get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Haydovchi profili topilmadi")
    attempt = await dispatch_service.get_active_attempt(db, driver.id)
    if not attempt:
        return None

    # DIQQAT: `DispatchAttempt.order` — ORM relationship, `DispatchAttemptResponse.order`
    # esa DispatchOrderSummary. `model_validate(attempt)` ni to'g'ridan-to'g'ri chaqirish
    # relationshipni o'qiydi va (eager yuklanmagan bo'lsa) async kontekstda MissingGreenlet
    # bilan yiqiladi. Shu sabab javob maydonlari qo'lda yig'iladi; `order` xulosasi esa
    # get_active_attempt selectinload bilan oldindan yuklab bergan obyektdan olinadi —
    # pending paytida haydovchi buyurtmani `GET /orders/{id}` orqali o'qiy olmaydi (403).
    order = attempt.order
    summary: Optional[schemas.DispatchOrderSummary] = None
    if order is not None:
        origin, destination = order.origin, order.destination
        summary = schemas.DispatchOrderSummary(
            cargo_name=order.cargo_name,
            weight=order.weight,
            price=order.price,
            currency=order.currency,
            origin_address=origin.address if origin else None,
            destination_address=destination.address if destination else None,
            # A→B masofasi va marshrut chizig'i — haydovchi taklifni ko'rishdayoq
            # yo'nalishni xaritada baholay olishi uchun (attempt.distance_km esa
            # haydovchidan A nuqtagacha bo'lgan masofa, bu bilan chalkashtirmaslik kerak).
            total_distance_km=order.total_distance_km,
            origin_latitude=float(origin.latitude) if origin else None,
            origin_longitude=float(origin.longitude) if origin else None,
            destination_latitude=float(destination.latitude) if destination else None,
            destination_longitude=float(destination.longitude) if destination else None,
            route_geometry=await crud.get_order_route_geometry(db, order.id),
        )

    return schemas.DispatchAttemptResponse(
        id=attempt.id,
        order_id=attempt.order_id,
        driver_id=attempt.driver_id,
        round_number=attempt.round_number,
        match_type=attempt.match_type,
        distance_km=attempt.distance_km,
        status=attempt.status,
        sent_at=attempt.sent_at,
        expires_at=attempt.expires_at,
        order=summary,
    )


@router.post("/dispatch/{attempt_id}/accept", response_model=schemas.OrderDetailResponse,
             summary="Haydovchi navbat bilan kelgan taklifni qabul qiladi")
async def accept_dispatch(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Faqat haydovchilar uchun")
    try:
        order = await dispatch_service.accept_attempt(db, attempt_id, acting_user_id=current_user.id)
    except dispatch_service.DispatchError as exc:
        _raise_dispatch_error(exc)
    return schemas.OrderDetailResponse.from_order(order)


@router.post("/dispatch/{attempt_id}/reject", status_code=status.HTTP_204_NO_CONTENT,
             summary="Haydovchi taklifni rad etadi — navbat keyingi nomzodga o'tadi")
async def reject_dispatch(
    attempt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role != UserRole.DRIVER:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Faqat haydovchilar uchun")
    try:
        await dispatch_service.reject_attempt(db, attempt_id, acting_user_id=current_user.id)
    except dispatch_service.DispatchError as exc:
        _raise_dispatch_error(exc)


async def _require_own_order(db: AsyncSession, order_id: int, current_user: User) -> Order:
    """Buyurtmani topadi va uning egasi hozirgi sender ekanini tekshiradi."""
    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Buyurtma topilmadi")
    if order.customer_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Bu buyurtma sizga tegishli emas")
    return order


@router.get("/{order_id}/price-options", response_model=schemas.OrderPriceOptionsResponse,
            summary="Narx tahrirlash ekrani uchun chegara va 5 ta tayyor variant")
async def get_order_price_options(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_sender),
):
    order = await _require_own_order(db, order_id, current_user)
    return await crud.get_order_price_options(db, order)


@router.patch("/{order_id}/price", response_model=schemas.OrderDetailResponse,
              summary="Sender narxni qo'lda o'zgartiradi (oshirish cheksiz, chegirma cheklangan)")
async def set_custom_price(
    order_id: int,
    data: schemas.CustomPriceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_sender),
):
    """Narxni oshirish cheklanmagan; pasaytirish `SENDER_MAX_DISCOUNT_PERCENT`
    (standart 15%) bilan chegaralangan — chegaradan past narx 400 qaytaradi."""
    order = await _require_own_order(db, order_id, current_user)
    try:
        order = await crud.set_custom_price(db, order, data.price)
    except pricing.PriceValidationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return schemas.OrderDetailResponse.from_order(order)


@router.post("/{order_id}/price-bump", response_model=schemas.OrderDetailResponse,
             summary="Sender narxni oshirib qidiruvni davom ettiradi (5 urinish rad etilgandan keyin)")
async def price_bump_order(
    order_id: int,
    data: schemas.PriceBumpRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_sender),
):
    order = await crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Buyurtma topilmadi")
    if order.customer_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Faqat buyurtma egasi narxni oshira oladi")
    try:
        order = await dispatch_service.apply_price_bump(db, order, data.price)
    except dispatch_service.DispatchError as exc:
        _raise_dispatch_error(exc)
    return schemas.OrderDetailResponse.from_order(order)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Buyurtmani bekor qilish (egasi)")
async def cancel_order(
    order_id: int,
    reason: Optional[str] = Query(None, max_length=300, description="Bekor qilish sababi"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Buyurtmani bekor qiladi (CANCELLED).

    Ilgari bu qattiq `DELETE` edi — buyurtma va uning butun tarixi izsiz yo'qolardi.
    Endi yozuv saqlanadi: kim, qachon va nima sababdan bekor qilgani ma'lum bo'ladi.

    Yuk allaqachon ortilgan bo'lsa (`IN_PROGRESS`) mijoz o'zi bekor qila olmaydi —
    haydovchi yo'lda va bu pul/mas'uliyat masalasi, shuning uchun admin aralashadi.
    """
    order = await _require_order_access(db, order_id, current_user)
    is_admin = _is_admin(current_user)
    if not is_admin and order.customer_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Faqat buyurtma egasi bekor qila oladi")

    if not is_admin and order.status == OrderStatus.IN_PROGRESS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Yuk allaqachon ortilgan — buyurtmani o'zingiz bekor qila olmaysiz. "
                "Administratsiyaga murojaat qiling."
            ),
        )

    # Kim bekor qilmoqda: buyurtma egasi ("sender") yoki admin.
    deleted_by = "sender" if order.customer_id == current_user.id else "admin"

    cargo_name = order.cargo_name
    assigned_driver_id = order.driver_id

    # Ochiq taklif xabarining manzili — bekor qilishdan OLDIN o'qiladi (keyin urinish
    # CANCELLED bo'lib, so'rov uni topmay qoladi). Bot handleri ham shu yordamchini
    # ishlatadi (`handlers/dispatch.py`), shuning uchun mantiq bir joyda.
    pending_offer = await dispatch_service.get_pending_offer_message(db, order)

    # Bekor qilish (commit bilan). Faqat shu muvaffaqiyatli tugagach xabar yuboramiz —
    # aks holda DB xatosida buyurtma bekor bo'lmay qoladi-yu, haydovchi "bekor qilindi"
    # xabarini olib ishni to'xtatadi (mos kelmaydigan holat).
    # Terminal holatdagi buyurtmani bekor qilib bo'lmasligi `OrderFlowError` bilan
    # bildiriladi va global handler uni 400 qilib qaytaradi (yuqoridagi kabi).
    await crud.cancel_order(db, order, cancelled_by_user_id=current_user.id, reason=reason)

    # Xabarnoma (Telegram xatosi bo'lsa ham bekor qilish allaqachon yakunlangan —
    # notifications.* funksiyalari exception tashlamaydi, faqat log yozadi).
    if assigned_driver_id is not None:
        # ACCEPTED/IN_PROGRESS — biriktirilgan haydovchiga bekor qilingani haqida xabar.
        await notifications.notify_drivers_order_deleted(
            db, assigned_driver_id, cargo_name, deleted_by=deleted_by
        )
    else:
        # PENDING — faol taklif yuborilgan haydovchining bot xabarini tahrirlaymiz
        # (urinishning o'zi `cancel_order` ichida CANCELLED qilib yopilgan).
        await dispatch_service.notify_offer_cancelled(pending_offer)
