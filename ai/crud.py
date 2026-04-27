from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from typing import List, Optional
from ai.models import (
    Chat, Message, Attachment, Rating, AIAnalysis, AICommand
)
from ai.schemas import (
    ChatCreate, ChatUpdate,
    MessageCreate, MessageUpdate,
    RatingCreate, RatingUpdate,
    AIAnalysisCreate, AICommandCreate, AICommandUpdate
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
    result = await db.execute(select(Chat).where(Chat.user_id == user_id))
    return result.scalars().all()

async def update_chat(db: AsyncSession, pk: int, data: ChatUpdate) -> Optional[Chat]:
    """Chat holati (status) yoki kategoriyasini o'zgartiradi."""
    await db.execute(update(Chat).where(Chat.id == pk).values(**data.model_dump(exclude_unset=True)))
    await db.commit()
    return await get_chat(db, pk)

# ════════════════════════════════════════════════
# MESSAGE CRUD - Xabarlar bilan ishlash
# ════════════════════════════════════════════════

async def create_message(db: AsyncSession, data: MessageCreate) -> Message:
    """
    Chatga yangi xabar qo'shadi. 
    Agar xabar ichida rasm yoki ovoz kabi fayllar bo'lsa, ular ham birga saqlanadi.
    """
    msg_data = data.model_dump()
    attachments_data = msg_data.pop('attachments', []) or []
    
    msg_obj = Message(**msg_data)
    db.add(msg_obj)
    await db.flush() # ID olish uchun
    
    for att_data in attachments_data:
        att = Attachment(message_id=msg_obj.id, **att_data)
        db.add(att)
    
    await db.commit()
    await db.refresh(msg_obj)
    return msg_obj

async def get_message(db: AsyncSession, pk: int) -> Optional[Message]:
    """Bitta xabarni barcha fayllari bilan yuklaydi."""
    result = await db.execute(
        select(Message).options(selectinload(Message.attachments)).where(Message.id == pk)
    )
    return result.scalar_one_or_none()

async def mark_messages_as_read(db: AsyncSession, chat_id: int):
    """Chatdagi o'qilmagan barcha xabarlarni 'o'qilgan' holatiga o'tkazadi."""
    await db.execute(
        update(Message).where(Message.chat_id == chat_id, Message.is_read == False).values(is_read=True)
    )
    await db.commit()

async def update_message(db: AsyncSession, pk: int, data: MessageUpdate) -> Optional[Message]:
    """
    Xabar matnini tahrirlaydi (agar user o'zi yozgan bo'lsa).
    Tahrirlangan vaqtni (edited_at) avtomatik belgilanadi.
    """
    update_data = data.model_dump(exclude_unset=True)
    update_data['edited_at'] = datetime.now(timezone.utc)
    
    await db.execute(update(Message).where(Message.id == pk).values(**update_data))
    await db.commit()
    return await get_message(db, pk)

async def delete_message(db: AsyncSession, pk: int) -> bool:
    """Xabarni o'chiradi."""
    await db.execute(delete(Message).where(Message.id == pk))
    await db.commit()
    return True

# ════════════════════════════════════════════════
# RATING CRUD - Baholash tizimi
# ════════════════════════════════════════════════

async def create_rating(db: AsyncSession, data: RatingCreate) -> Rating:
    """
    Safar yakunida User yoki Driver uchun baho qo'shadi.
    Bu ma'lumot keyinchalik AI tomonidan tahlil qilinishi mumkin.
    """
    obj = Rating(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def get_rating(db: AsyncSession, pk: int) -> Optional[Rating]:
    """Bahoni ID bo'yicha olish."""
    result = await db.execute(select(Rating).where(Rating.id == pk))
    return result.scalar_one_or_none()

# ════════════════════════════════════════════════
# AI ANALYSIS & COMMAND CRUD
# ════════════════════════════════════════════════

async def create_ai_analysis(db: AsyncSession, data: AIAnalysisCreate) -> AIAnalysis:
    """AI tomonidan o'tkazilgan tahlil natijasini saqlaydi (masalan: shikoyatni tekshirish)."""
    obj = AIAnalysis(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def create_ai_command(db: AsyncSession, data: AICommandCreate) -> AICommand:
    """Ovozli yoki yozma buyruqni navbatga qo'shadi."""
    obj = AICommand(**data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj

async def update_ai_command(db: AsyncSession, pk: int, data: AICommandUpdate) -> Optional[AICommand]:
    """Buyruq bajarilgandan so'ng natijani yoki xatolikni yangilaydi."""
    update_data = data.model_dump(exclude_unset=True)
    if 'status' in update_data and update_data['status'] in ('success', 'failed'):
        update_data['executed_at'] = datetime.now(timezone.utc)
        
    await db.execute(update(AICommand).where(AICommand.id == pk).values(**update_data))
    await db.commit()
    result = await db.execute(select(AICommand).where(AICommand.id == pk))
    return result.scalar_one_or_none()
