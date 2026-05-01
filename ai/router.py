import os
import shutil
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from config.config import get_db, async_session
from ai import crud, schemas, agent
from ai.websocket import manager
from users.auth import get_current_user
from users.models import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["Logistika AI & Chat"])

# ════════════════════════════════════════════════
# WEBSOCKET - Real-vaqtda muloqot va AI Agent
# ════════════════════════════════════════════════

@router.get("/ws-info", tags=["Documentation"])
async def websocket_info():
    """AI Agent va Chat uchun WebSocket qo'llanmasi."""
    return {
        "url": "ws://domain/api/ai/ws/{chat_id}?token=YOUR_ACCESS_TOKEN",
        "authentication": "JWT token debe berilishi kerak query parameter sifatida",
        "token_example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "how_to_get_token": "POST /api/auth/login orqali access token olish",
        "events_sent_by_user": [
            {"type": "new_message", "content": "Xabar matni", "sender_id": 123}
        ],
        "events_received_from_ai": [
            {"event": "new_message", "data": {...}},
            {"event": "ai_action", "action": "Order yaratilmoqda..."}
        ],
        "error_codes": {
            "1008": "Policy violation - Invalid token or no access to chat"
        }
    }

@router.websocket("/ws/{chat_id}")
async def websocket_endpoint(websocket: WebSocket, chat_id: int):
    """
    Mukkammal AI Agent va Chat interfeysi.
    Foydalanuvchi xabar yuboradi -> AI agent tahlil qiladi -> Tool ishlatadi -> Javob qaytaradi.
    
    ⚠️ AUTHENTICATION: WebSocket connection token query parameter orqali yuborishi kerak:
    ws://localhost:8000/api/ai/ws/123?token=eyJhbGc...
    """
    from ai.websocket import verify_websocket_token
    
    # ─────────────────────────────────────────────────────────────
    # STEP 1: Token orqali user_id extract qilish
    # ─────────────────────────────────────────────────────────────
    token = websocket.query_params.get("token")
    user_id = verify_websocket_token(token)
    
    if user_id is None:
        # Token yaroqsiz yoki yo'q - ulanishni rad qilish
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="❌ Invalid or missing authentication token")
        logger.warning(f"❌ WebSocket connection rejected for chat {chat_id}: Invalid token")
        return
    
    # ─────────────────────────────────────────────────────────────
    # STEP 2: Chat ga foydalanuvchi ruxsati borligini tekshirish
    # ─────────────────────────────────────────────────────────────
    async with async_session() as db:
        chat_obj = await crud.get_chat(db, chat_id)
        if not chat_obj:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="❌ Chat not found")
            logger.warning(f"❌ WebSocket: Chat {chat_id} not found")
            return
        
        # Chat ga ruxsat tekshirish (chat owner bo'lishi kerak)
        if chat_obj.user_id != user_id and (chat_obj.driver_id != user_id if hasattr(chat_obj, 'driver_id') else True):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="❌ Access denied")
            logger.warning(f"❌ WebSocket: User {user_id} tried to access chat {chat_id} without permission")
            return
    
    # ─────────────────────────────────────────────────────────────
    # STEP 3: Ulanish qabul qilish
    # ─────────────────────────────────────────────────────────────
    await manager.connect(websocket, chat_id, user_id)
    logger.info(f"✅ WebSocket authenticated: User {user_id} connected to chat {chat_id}")
    
    log_agent = agent.LogistikaAgent(user_id=user_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "new_message":
                content = data.get("content")
                sender_id = data.get("sender_id", user_id)
                
                # 1. Foydalanuvchi xabarini bazaga saqlash
                async with async_session() as db:
                    user_msg = await crud.create_message(db, schemas.MessageCreate(
                        chat_id=chat_id,
                        sender_id=sender_id,
                        sender_type=schemas.SenderType.USER,
                        content=content
                    ))
                    
                    # Foydalanuvchi xabarini hamma qatnashchilarga tarqatish
                    await manager.broadcast({
                        "event": "new_message",
                        "data": schemas.MessageResponse.model_validate(user_msg).model_dump(mode='json')
                    }, chat_id)

                # 2. AI Agent bilan ishlash (faqat AI kategoriyasidagi chatlar yoki maxsus buyruqlar uchun)
                # Chat turini tekshirish
                async with async_session() as db:
                    chat_obj = await crud.get_chat(db, chat_id)
                    is_ai_chat = chat_obj and chat_obj.category == schemas.ChatCategory.AI_COMMAND
                
                if is_ai_chat or content.lower().startswith("ai"):
                    # Frontend uchun callback: AI harakatini bildirish
                    async def ai_action_callback(action_text: str):
                        await manager.broadcast({
                            "event": "ai_action",
                            "action": action_text
                        }, chat_id)

                    # AI javobini olish
                    ai_response_text = await log_agent.process_message(
                        content, 
                        chat_id=chat_id, 
                        on_action_callback=ai_action_callback
                    )
                    
                    # 3. AI javobini bazaga saqlash
                    async with async_session() as db:
                        ai_msg = await crud.create_message(db, schemas.MessageCreate(
                            chat_id=chat_id,
                            sender_id=0, # AI ID
                            sender_type=schemas.SenderType.AI,
                            content=ai_response_text
                        ))
                        
                        # AI javobini tarqatish
                        await manager.broadcast({
                            "event": "new_message",
                            "data": schemas.MessageResponse.model_validate(ai_msg).model_dump(mode='json')
                        }, chat_id)

    except WebSocketDisconnect:
        manager.disconnect(chat_id, user_id)
        logger.info(f"WebSocket disconnected: User {user_id} from chat {chat_id}")
    except Exception as e:
        logger.error(f"❌ WebSocket Error in chat {chat_id}: {e}", exc_info=True)
        manager.disconnect(chat_id, user_id)

# ════════════════════════════════════════════════
# REST ENDPOINTS - Qolgan amallar
# ════════════════════════════════════════════════

@router.post("/chats", response_model=schemas.ChatResponse, summary="Yangi chat yaratish")
async def create_new_chat(
    data: schemas.ChatBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chat_data = schemas.ChatCreate(
        user_id=current_user.id,
        **data.model_dump()
    )
    return await crud.create_chat(db, chat_data)

@router.get("/chats", response_model=List[schemas.ChatResponse], summary="Mening chatlarim")
async def list_my_chats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return await crud.list_user_chats(db, current_user.id)

@router.get("/chats/{chat_id}", response_model=schemas.ChatResponse, summary="Chat tafsilotlari")
async def get_chat_details(
    chat_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bitta chatni barcha xabarlari (history) bilan olish."""
    chat = await crud.get_chat(db, chat_id)
    if not chat or chat.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Chat topilmadi yoki sizga tegishli emas")
    return chat

@router.patch("/messages/{message_id}", response_model=schemas.MessageResponse, summary="Xabarni tahrirlash")
async def edit_message(
    message_id: int,
    data: schemas.MessageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    msg = await crud.get_message(db, message_id)
    if not msg or msg.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="Ruxsat berilmagan")
    
    updated_msg = await crud.update_message(db, message_id, data)
    await manager.broadcast({
        "event": "message_edited",
        "data": schemas.MessageResponse.model_validate(updated_msg).model_dump(mode='json')
    }, msg.chat_id)
    return updated_msg

@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xabarni o'chirish")
async def delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    msg = await crud.get_message(db, message_id)
    if not msg or msg.sender_id != current_user.id:
        raise HTTPException(status_code=403, detail="Ruxsat berilmagan")
    
    chat_id = msg.chat_id
    await crud.delete_message(db, message_id)
    await manager.broadcast({"event": "message_deleted", "message_id": message_id}, chat_id)
    return None

from config.config import get_db, async_session, UPLOAD_DIR, STATIC_PATH

# ...

@router.post("/upload", response_model=dict, summary="Media yuklash")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    file_ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    return {"url": f"{STATIC_PATH}/{unique_filename}", "filename": file.filename}

@router.post("/ratings", response_model=schemas.RatingResponse, summary="Baho berish")
async def submit_rating(
    data: schemas.RatingBase,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rating_data = schemas.RatingCreate(
        rated_by_user=current_user.id if data.target_type == schemas.RatingTarget.DRIVER else None,
        rated_by_driver=current_user.id if data.target_type == schemas.RatingTarget.USER else None,
        **data.model_dump()
    )
    return await crud.create_rating(db, rating_data)
