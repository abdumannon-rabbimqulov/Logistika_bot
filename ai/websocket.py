from fastapi import WebSocket
from typing import Dict, Optional
import logging
from jose import jwt, JWTError
from config.config import SECRET_KEY, ALGORITHM

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════
# CONNECTION MANAGER - Real-vaqtda aloqa boshqaruvchisi
# ════════════════════════════════════════════════

class ConnectionManager:
    """
    WebSocket ulanishlarini chat_id bo'yicha guruhlaydi.
    Xabar kelganda faqat o'sha chatdagi qatnashchilarga yuboradi (Broadcast).
    """
    def __init__(self):
        # Strukturasi: {chat_id: {user_id: WebSocket}}
        self.active_connections: Dict[int, Dict[int, WebSocket]] = {}

    async def connect(self, websocket: WebSocket, chat_id: int, user_id: int):
        """Yangi foydalanuvchi chatga ulanganda chaqiriladi."""
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = {}
        self.active_connections[chat_id][user_id] = websocket
        logger.info(f"✅ User {user_id} connected to chat {chat_id}")

    def disconnect(self, chat_id: int, user_id: int):
        """Foydalanuvchi chatdan chiqqanda yoki aloqa uzilganda."""
        if chat_id in self.active_connections:
            if user_id in self.active_connections[chat_id]:
                del self.active_connections[chat_id][user_id]
                logger.info(f"❌ User {user_id} disconnected from chat {chat_id}")
            # Agar chatda hech kim qolmasa, xotirani bo'shatamiz
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]

    async def broadcast(self, message: dict, chat_id: int):
        """Ma'lum bir chatdagi barcha aktiv foydalanuvchilarga ma'lumot yuboradi."""
        if chat_id in self.active_connections:
            disconnected_users = []
            for user_id, connection in self.active_connections[chat_id].items():
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"⚠️  Failed to send message to user {user_id}: {e}")
                    disconnected_users.append(user_id)
            
            # Clean up disconnected users
            for user_id in disconnected_users:
                self.disconnect(chat_id, user_id)


def verify_websocket_token(token: Optional[str]) -> Optional[int]:
    """
    WebSocket token'ni verify qiladi va user_id qaytaradi.
    ❌ Agar token yaroqsiz bo'lsa None qaytaradi.
    """
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Token turini tekshirish (access token bo'lishi kerak)
        if payload.get("type") != "access":
            logger.warning("❌ WebSocket token type is not 'access'")
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("❌ WebSocket token missing 'sub' (user_id)")
            return None
        
        return int(user_id)
    
    except JWTError as e:
        logger.warning(f"❌ Invalid WebSocket token: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Token verification error: {e}")
        return None


manager = ConnectionManager()
