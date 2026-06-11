from fastapi import WebSocket
from typing import Dict, Optional, List
import logging
from jose import jwt, JWTError
from config.config import SECRET_KEY, ALGORITHM

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    WebSocket ulanishlarini chat_id bo'yicha guruhlaydi.
    Telegram-like delivery: send_to, broadcast, online_users methodlari.
    Strukturasi: {chat_id: {user_id: WebSocket}}
    """

    def __init__(self):
        self.active_connections: Dict[int, Dict[int, WebSocket]] = {}

    # ── Lifecycle ──────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, chat_id: int, user_id: int) -> None:
        """Yangi foydalanuvchi chatga ulanganda chaqiriladi."""
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = {}
        self.active_connections[chat_id][user_id] = websocket
        logger.info("✅ WS connect: user=%s chat=%s", user_id, chat_id)

    def disconnect(self, chat_id: int, user_id: int) -> None:
        """Foydalanuvchi chatdan chiqqanda yoki aloqa uzilganda."""
        if chat_id in self.active_connections:
            self.active_connections[chat_id].pop(user_id, None)
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]
        logger.info("❌ WS disconnect: user=%s chat=%s", user_id, chat_id)

    # ── Presence ───────────────────────────────────────────────────

    def is_online(self, chat_id: int, user_id: int) -> bool:
        """Foydalanuvchi hozir chatda online-mi?"""
        return user_id in self.active_connections.get(chat_id, {})

    def online_users(self, chat_id: int) -> List[int]:
        """Chatdagi barcha online foydalanuvchilar ID si."""
        return list(self.active_connections.get(chat_id, {}).keys())

    # ── Sending ────────────────────────────────────────────────────

    async def send_to(self, user_id: int, chat_id: int, payload: dict) -> bool:
        """
        Muayyan foydalanuvchiga xabar yuboradi.
        Muvaffaqiyatli bo'lsa True, ulanmagan bo'lsa False qaytaradi.
        """
        ws = self.active_connections.get(chat_id, {}).get(user_id)
        if ws:
            try:
                await ws.send_json(payload)
                return True
            except Exception as exc:
                logger.warning("send_to failed user=%s: %s", user_id, exc)
                self.disconnect(chat_id, user_id)
        return False

    async def broadcast(
        self,
        message: dict,
        chat_id: int,
        exclude_user: Optional[int] = None,
    ) -> List[int]:
        """
        Chatdagi barcha aktiv foydalanuvchilarga xabar yuboradi.
        exclude_user ni o'tkazib yuboradi.
        Xabar yetgan user_id lar ro'yxatini qaytaradi (delivery uchun).
        """
        delivered_to: List[int] = []
        disconnected: List[int] = []

        for uid, ws in list(self.active_connections.get(chat_id, {}).items()):
            if uid == exclude_user:
                continue
            try:
                await ws.send_json(message)
                delivered_to.append(uid)
            except Exception as exc:
                logger.warning("broadcast failed user=%s: %s", uid, exc)
                disconnected.append(uid)

        for uid in disconnected:
            self.disconnect(chat_id, uid)

        return delivered_to


def verify_websocket_token(token: Optional[str]) -> Optional[int]:
    """
    WebSocket token'ni verify qiladi va user_id qaytaradi.
    ❌ Agar token yaroqsiz bo'lsa None qaytaradi.
    """
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "access":
            logger.warning("❌ WebSocket token type is not 'access'")
            return None

        user_id = payload.get("sub")
        if not user_id:
            logger.warning("❌ WebSocket token missing 'sub' (user_id)")
            return None

        return int(user_id)

    except JWTError as e:
        logger.warning("❌ Invalid WebSocket token: %s", e)
        return None
    except Exception as e:
        logger.error("❌ Token verification error: %s", e)
        return None


manager = ConnectionManager()
