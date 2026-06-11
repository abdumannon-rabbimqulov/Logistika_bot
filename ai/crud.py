from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from ai.models import (
    Chat,
    ChatCategory,
    ChatStatus,
    Message,
    Attachment,
    Rating,
    AIAnalysis,
    AICommand,
    SenderType,
)
from ai import schemas
from ai.schemas import (
    ChatCreate,
    ChatUpdate,
    MessageCreate,
    MessageUpdate,
    RatingCreate,
    RatingUpdate,
    AIAnalysisCreate,
    AICommandCreate,
    AICommandUpdate,
)
from datetime import datetime, timezone

# ════════════════════════════════════════════════
# CHAT CRUD - Suhbat sessiyalarini boshqarish
# ════════════════════════════════════════════════

async def create_chat(db: AsyncSession, data: ChatCreate) -> Chat:
    """
    Yangi chat sessiyasini yaratadi. 
    Bu User va Driver o'rtasida yoki AI bilan muloqot uchun ishlatiladi.
    """
    obj = Chat(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def get_chat(db: AsyncSession, pk: int) -> Optional[Chat]:
    """
    ID bo'yicha chatni topadi va unga tegishli barcha xabarlar va biriktirilgan fayllarni yuklaydi.
    """
    result = await db.execute(
        select(Chat)
        .options(selectinload(Chat.messages).selectinload(Message.attachments))
        .where(Chat.id == pk)
    )
    return result.scalar_one_or_none()

async def list_user_chats(db: AsyncSession, user_id: int) -> List[Chat]:
    """Foydalanuvchining barcha chat sessiyalarini qaytaradi."""
    from driver.models import Driver
    driver_stmt = select(Driver.id).where(Driver.user_id == user_id)
    driver_result = await db.execute(driver_stmt)
    driver_id = driver_result.scalar_one_or_none()

    if driver_id is not None:
        stmt = (
            select(Chat)
            .where((Chat.user_id == user_id) | (Chat.driver_id == driver_id))
            .order_by(Chat.created_at.desc())
        )
    else:
        stmt = select(Chat).where(Chat.user_id == user_id).order_by(Chat.created_at.desc())

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_or_create_ai_chat(db: AsyncSession, user_id: int) -> Chat:
    """Foydalanuvchi uchun AI yordamchi chatini topadi yoki yaratadi."""
    result = await db.execute(
        select(Chat)
        .where(
            Chat.user_id == user_id,
            Chat.category == ChatCategory.AI_COMMAND,
            Chat.status == ChatStatus.OPEN,
        )
        .order_by(Chat.created_at.desc())
        .limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    return await create_chat(
        db,
        ChatCreate(
            user_id=user_id,
            category=schemas.ChatCategory.AI_COMMAND,
            title="Logistika AI",
        ),
    )


async def list_chat_messages(
    db: AsyncSession,
    chat_id: int,
    *,
    limit: int = 50,
    before_id: Optional[int] = None,
) -> List[Message]:
    """Chat xabarlarini vaqt bo'yicha (eskidan yangiga) qaytaradi."""
    stmt = (
        select(Message)
        .options(selectinload(Message.attachments))
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .limit(min(limit, 100))
    )
    if before_id is not None:
        stmt = stmt.where(Message.id < before_id)
    result = await db.execute(stmt)
    return list(reversed(result.scalars().all()))


async def build_agent_history(
    db: AsyncSession,
    chat_id: int,
    *,
    limit: int = 24,
    exclude_message_id: Optional[int] = None,
) -> List[dict]:
    """Gemini uchun suhbat konteksti."""
    messages = await list_chat_messages(db, chat_id, limit=limit + 1)
    history: List[dict] = []
    for msg in messages:
        if exclude_message_id and msg.id == exclude_message_id:
            continue
        text = (msg.content or "").strip()
        if not text:
            continue
        if msg.sender_type == SenderType.AI:
            history.append({"role": "model", "text": text})
        elif msg.sender_type in (SenderType.USER, SenderType.DRIVER):
            history.append({"role": "user", "text": text})
    return history[-limit:]

async def update_chat(db: AsyncSession, pk: int, data: ChatUpdate) -> Optional[Chat]:
    """Chat holati (status) yoki kategoriyasini o'zgartiradi."""
    await db.execute(update(Chat).where(Chat.id == pk).values(**data.model_dump(exclude_unset=True)))
    await db.commit()
    return await get_chat(db, pk)

# ════════════════════════════════════════════════
# MESSAGE CRUD - Xabarlar bilan ishlash
# ════════════════════════════════════════════════

async def create_message(db: AsyncSession, data: MessageCreate) -> Message:

    msg_data = data.model_dump()
    attachments_data = msg_data.pop('attachments', []) or []
    
    msg_obj = Message(**msg_data)
    db.add(msg_obj)
    await db.flush() 
    
    for att_data in attachments_data:
        att = Attachment(message_id=msg_obj.id, **att_data)
        db.add(att)
    
    await db.commit()
    await db.refresh(msg_obj)
    return msg_obj

async def get_message(db: AsyncSession, pk: int) -> Optional[Message]:
    result = await db.execute(
        select(Message).options(selectinload(Message.attachments)).where(Message.id == pk)
    )
    return result.scalar_one_or_none()

async def mark_messages_as_read(db: AsyncSession, chat_id: int):
    await db.execute(
        update(Message).where(Message.chat_id == chat_id, Message.is_read == False).values(is_read=True)
    )
    await db.commit()

async def update_message(db: AsyncSession, pk: int, data: MessageUpdate) -> Optional[Message]:

    update_data = data.model_dump(exclude_unset=True)
    update_data['edited_at'] = datetime.now(timezone.utc)
    
    await db.execute(update(Message).where(Message.id == pk).values(**update_data))
    await db.commit()
    return await get_message(db, pk)

async def delete_message(db: AsyncSession, pk: int) -> bool:
    await db.execute(delete(Message).where(Message.id == pk))
    await db.commit()
    return True


async def create_rating(db: AsyncSession, data: RatingCreate) -> Rating:

    obj = Rating(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def get_rating(db: AsyncSession, pk: int) -> Optional[Rating]:
    result = await db.execute(select(Rating).where(Rating.id == pk))
    return result.scalar_one_or_none()



async def create_ai_analysis(db: AsyncSession, data: AIAnalysisCreate) -> AIAnalysis:
    obj = AIAnalysis(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def create_ai_command(db: AsyncSession, data: AICommandCreate) -> AICommand:
    obj = AICommand(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def update_ai_command(db: AsyncSession, pk: int, data: AICommandUpdate) -> Optional[AICommand]:
    update_data = data.model_dump(exclude_unset=True)
    if 'status' in update_data and update_data['status'] in ('success', 'failed'):
        update_data['executed_at'] = datetime.now(timezone.utc)
        
    await db.execute(update(AICommand).where(AICommand.id == pk).values(**update_data))
    await db.commit()
    result = await db.execute(select(AICommand).where(AICommand.id == pk))
    return result.scalar_one_or_none()
