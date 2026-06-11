from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from config.config import get_db
from driver import crud as driver_crud
from order import crud, schemas
from order.models import Order, OrderStatus
from users.auth import get_current_sender, get_current_user
from users.models import User, UserRole

router = APIRouter(prefix="/orders", tags=["Buyurtmalar (Orders)"])


def _ensure_sender_owns_order(order: Order, sender: User) -> None:
    if order.customer_id != sender.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu buyurtma sizga tegishli emas.",
        )


async def _get_order_or_404(db: AsyncSession, pk: int) -> Order:
    order = await crud.get_order(db, pk)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyurtma topilmadi.")
    return order


async def _validate_truck_type(db: AsyncSession, truck_type_id: int) -> None:
    truck = await driver_crud.get_truck_type(db, truck_type_id)
    if not truck:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mashina turi topilmadi (id={truck_type_id}).",
        )
    if not truck.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mashina turi faol emas (id={truck_type_id}).",
        )


# --- Order Endpoints ---


@router.post(
    "/",
    response_model=schemas.OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi buyurtma yaratish (faqat sender)",
)
async def create_order(
    data: schemas.OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_sender),
):
    """Mijoz yangi yuk buyurtmasi. GPS koordinatalar har bir waypoint uchun majburiy.

    `customer_id` JWT dan olinadi; `required_truck_type_id` majburiy va bazada mavjud bo'lishi kerak.
    """
    await _validate_truck_type(db, data.required_truck_type_id)
    return await crud.create_order(db, data, customer_id=current_user.id)


@router.get("/", response_model=List[schemas.OrderResponse], summary="Buyurtmalar ro'yxati")
async def list_orders(
    customer_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    status: Optional[str] = None,
    required_truck_type_id: Optional[int] = Query(
        None, description="Mashina turi bo'yicha filtr (haydovchi uchun)"
    ),
    unassigned_only: bool = Query(
        False, description="Faqat haydovchisiz buyurtmalar (driver_id IS NULL)"
    ),
    filter_by_truck: bool = Query(
        False,
        description="Haydovchi uchun: faqat o'z mashina turiga mos buyurtmalar",
    ),
    match_my_truck: bool = Query(
        False,
        description="(Eski) filter_by_truck=true bilan bir xil",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Waypoints sequence bo'yicha tartiblangan ro'yxat."""
    from driver.crud import get_driver_by_user_id

    parsed_status = crud.parse_order_status(status)
    apply_truck_filter = filter_by_truck or match_my_truck

    # Sender faqat o'z buyurtmalarini ko'radi
    if current_user.role == UserRole.SENDER:
        if customer_id is not None and customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Boshqa mijoz buyurtmalarini ko'rish mumkin emas.",
            )
        return await crud.get_all_orders(
            db,
            customer_id=current_user.id,
            driver_id=driver_id,
            status=status,
            required_truck_type_id=required_truck_type_id,
            unassigned_only=unassigned_only,
        )

    is_driver_marketplace = (
        current_user.role == UserRole.DRIVER
        and customer_id is None
        and driver_id is None
    )
    if is_driver_marketplace:
        driver = await get_driver_by_user_id(db, current_user.id)
        truck_filter_id: Optional[int] = None
        if apply_truck_filter:
            if not driver:
                raise HTTPException(
                    status_code=403,
                    detail="Haydovchi profili topilmadi — mashina turiga filtrlash mumkin emas",
                )
            if driver.is_blocked:
                raise HTTPException(status_code=403, detail="Haydovchi bloklangan")
            truck_filter_id = driver.truck_type_id

        marketplace_status = parsed_status or OrderStatus.PENDING
        return await crud.list_driver_marketplace_orders(
            db,
            status=marketplace_status,
            truck_type_id=truck_filter_id,
        )

    truck_type_id = required_truck_type_id
    only_unassigned = unassigned_only

    if apply_truck_filter:
        driver = await get_driver_by_user_id(db, current_user.id)
        if not driver:
            raise HTTPException(
                status_code=403,
                detail="Haydovchi profili topilmadi — mashina turiga filtrlash mumkin emas",
            )
        if driver.is_blocked:
            raise HTTPException(status_code=403, detail="Haydovchi bloklangan")
        truck_type_id = driver.truck_type_id

    if match_my_truck:
        only_unassigned = True

    return await crud.get_all_orders(
        db,
        customer_id,
        driver_id,
        status,
        required_truck_type_id=truck_type_id,
        unassigned_only=only_unassigned,
    )


@router.get("/{pk}", response_model=schemas.OrderResponse, summary="Buyurtma tafsilotlari")
async def get_order(
    pk: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bitta buyurtma. Sender — faqat o'z buyurtmasi; haydovchi — ko'rish uchun."""
    order = await _get_order_or_404(db, pk)

    if current_user.role == UserRole.SENDER:
        _ensure_sender_owns_order(order, current_user)

    return order


@router.patch(
    "/{pk}",
    response_model=schemas.OrderResponse,
    summary="Buyurtmani tahrirlash (faqat sender, o'z buyurtmasi)",
)
async def update_order(
    pk: int,
    data: schemas.OrderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_sender),
):
    """Mijoz o'z buyurtmasini yangilaydi."""
    order = await _get_order_or_404(db, pk)
    _ensure_sender_owns_order(order, current_user)
    return await crud.update_order(db, pk, data)


@router.delete(
    "/{pk}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Buyurtmani o'chirish (faqat sender, o'z buyurtmasi)",
)
async def delete_order(
    pk: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_sender),
):
    """Mijoz buyurtmani o'chiradi: takliflar → haydovchilarga xabar → buyurtma."""
    order = await _get_order_or_404(db, pk)
    _ensure_sender_owns_order(order, current_user)

    deleted = await crud.delete_order(db, pk, deleted_by="sender")
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Buyurtma topilmadi.")
    return None


@router.post(
    "/{order_id}/accept",
    response_model=schemas.OrderResponse,
    summary="Buyurtmani qabul qilish (haydovchi)",
)
async def accept_order_directly(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Haydovchi buyurtmani to'g'ridan-to'g'ri (taklif qilingan shartlar/narxda) qabul qiladi."""
    from driver.crud import get_driver_by_user_id
    from order.models import OrderOffer, OfferStatus
    from sqlalchemy import update

    driver = await get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faqat haydovchilar buyurtmani qabul qilishi mumkin.",
        )
    if driver.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Haydovchi bloklangan.",
        )

    order = await _get_order_or_404(db, order_id)
    if order.driver_id is not None or order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Buyurtma allaqachon band qilingan yoki faol emas.",
        )

    order.driver_id = driver.id
    order.status = OrderStatus.ACCEPTED

    # Qolgan barcha takliflarni OUTBID qilish
    await db.execute(
        update(OrderOffer)
        .where(OrderOffer.order_id == order.id)
        .values(status=OfferStatus.OUTBID)
    )

    # Yagona chat topish yoki yaratish
    from ai.models import Chat, ChatCategory, ChatStatus, Message, MessageType, SenderType, MessageStatus
    from sqlalchemy import select
    chat_stmt = select(Chat).where(
        Chat.user_id == order.customer_id,
        Chat.driver_id == driver.id,
        Chat.category == ChatCategory.CONVERSATION
    )
    chat_result = await db.execute(chat_stmt)
    existing_chat = chat_result.scalar_one_or_none()
    
    if not existing_chat:
        existing_chat = Chat(
            user_id=order.customer_id,
            driver_id=driver.id,
            category=ChatCategory.CONVERSATION,
            status=ChatStatus.OPEN,
            title="Mijoz va Haydovchi sirlari"
        )
        db.add(existing_chat)
        await db.flush()
        
    order.chat_id = existing_chat.id

    # Avtomat xabar yuborish
    system_msg_text = (
        f"📦 Yangi buyurtma kelishildi: {order.cargo_name}\n"
        f"💰 Narxi: {order.price} {order.currency}\n\n"
        f"Tafsilotlar: /sender/orders/{order.id}"
    )
    
    sys_msg = Message(
        chat_id=existing_chat.id,
        sender_type=SenderType.SYSTEM,
        message_type=MessageType.SYSTEM,
        content=system_msg_text,
        status=MessageStatus.SENT
    )
    db.add(sys_msg)

    await db.commit()
    full_order = await crud.get_order(db, order.id)
    
    # Telegram botga xabar
    from services.notifications import send_telegram_message
    if full_order.customer and full_order.customer.id:
        await send_telegram_message(full_order.customer.id, system_msg_text)
    if full_order.driver and full_order.driver.user and full_order.driver.user.id:
        await send_telegram_message(full_order.driver.user.id, system_msg_text)
        
    return full_order


# --- OrderOffer Endpoints ---


@router.post(
    "/{order_id}/offers",
    response_model=schemas.OrderOfferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Buyurtmaga taklif berish (haydovchi)",
)
async def create_offer(
    order_id: int,
    data: schemas.OrderOfferBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Haydovchi mijoz buyurtmasiga narx taklif qiladi."""
    from driver.crud import get_driver_by_user_id

    driver = await get_driver_by_user_id(db, current_user.id)
    if not driver:
        raise HTTPException(status_code=403, detail="Faqat haydovchilar taklif bera oladi")

    order = await _get_order_or_404(db, order_id)
    if order.driver_id is not None:
        raise HTTPException(status_code=400, detail="Buyurtmaga allaqachon haydovchi tayinlangan")

    offer_create = schemas.OrderOfferCreate(
        order_id=order_id,
        driver_id=driver.id,
        **data.model_dump(),
    )
    return await crud.create_order_offer(db, offer_create)


@router.get(
    "/{order_id}/offers",
    response_model=List[schemas.OrderOfferResponse],
    summary="Buyurtmaga kelgan takliflar (faqat sender)",
)
async def list_order_offers(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_sender),
):
    """Mijoz o'z buyurtmasiga kelgan takliflarni ko'radi."""
    order = await _get_order_or_404(db, order_id)
    _ensure_sender_owns_order(order, current_user)
    return await crud.get_order_offers(db, order_id)


@router.patch("/offers/{pk}", response_model=schemas.OrderOfferResponse, summary="Taklifni yangilash")
async def update_offer(
    pk: int,
    data: schemas.OrderOfferUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Taklifni qabul qilish yoki rad etish."""
    from order.models import Order, OrderOffer, OrderStatus, OfferStatus
    from ai.models import Chat, ChatCategory, ChatStatus
    from sqlalchemy import select, update
    from datetime import datetime, timezone

    offer = await crud.get_order_offer(db, pk)
    if not offer:
        raise HTTPException(status_code=404, detail="Taklif topilmadi")

    # If the user is accepting the offer
    is_accepting = False
    if data.status:
        status_val = data.status.value.lower() if hasattr(data.status, "value") else str(data.status).lower()
        if status_val == "accepted":
            is_accepting = True

    if is_accepting:
        order = await _get_order_or_404(db, offer.order_id)
        if order.driver_id is not None or order.status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail="Buyurtmaga allaqachon haydovchi tayinlangan yoki buyurtma faol emas.",
            )
        
        # Accept the offer
        offer.status = OfferStatus.ACCEPTED
        offer.accepted_at = datetime.now(timezone.utc)

        # Update order
        order.driver_id = offer.driver_id
        order.status = OrderStatus.ACCEPTED

        # Outbid all other offers for this order
        await db.execute(
            update(OrderOffer)
            .where(OrderOffer.order_id == order.id)
            .where(OrderOffer.id != offer.id)
            .where(OrderOffer.status.in_([OfferStatus.PENDING, OfferStatus.SEEN]))
            .values(status=OfferStatus.OUTBID)
        )

        # Yagona chat topish yoki yaratish
        from ai.models import Chat, ChatCategory, ChatStatus, Message, MessageType, SenderType, MessageStatus
        chat_stmt = select(Chat).where(
            Chat.user_id == order.customer_id,
            Chat.driver_id == offer.driver_id,
            Chat.category == ChatCategory.CONVERSATION
        )
        chat_result = await db.execute(chat_stmt)
        existing_chat = chat_result.scalar_one_or_none()
        
        if not existing_chat:
            existing_chat = Chat(
                user_id=order.customer_id,
                driver_id=offer.driver_id,
                category=ChatCategory.CONVERSATION,
                status=ChatStatus.OPEN,
                title="Mijoz va Haydovchi sirlari"
            )
            db.add(existing_chat)
            await db.flush()
            
        order.chat_id = existing_chat.id

        # Avtomat xabar yuborish
        system_msg_text = (
            f"📦 Yangi taklif qabul qilindi: {order.cargo_name}\n"
            f"💰 Narxi: {offer.offered_price} {offer.currency}\n\n"
            f"Tafsilotlar: /driver/orders/{order.id}"
        )
        
        sys_msg = Message(
            chat_id=existing_chat.id,
            sender_type=SenderType.SYSTEM,
            message_type=MessageType.SYSTEM,
            content=system_msg_text,
            status=MessageStatus.SENT
        )
        db.add(sys_msg)

        await db.commit()
        
        # Telegram botga xabar
        full_order = await crud.get_order(db, order.id)
        from services.notifications import send_telegram_message
        if full_order.customer and full_order.customer.id:
            await send_telegram_message(full_order.customer.id, system_msg_text)
        if full_order.driver and full_order.driver.user and full_order.driver.user.id:
            await send_telegram_message(full_order.driver.user.id, system_msg_text)
        await db.refresh(offer)
        return offer
    else:
        # Standard update
        return await crud.update_order_offer(db, pk, data)
