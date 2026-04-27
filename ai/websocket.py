from fastapi import WebSocket
from typing import Dict, List
import json

# ════════════════════════════════════════════════
# CONNECTION MANAGER - Real-vaqtda aloqa boshqaruvchisi
# ════════════════════════════════════════════════

class ConnectionManager:
    """
    WebSocket ulanishlarini chat_id bo'yicha guruhlaydi.
    Xabar kelganda faqat o'sha chatdagi qatnashchilarga yuboradi (Broadcast).
    """
    def __init__(self):
        # Strukturasi: {chat_id: [WebSocket, WebSocket, ...]}
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, chat_id: int):
        """Yangi foydalanuvchi chatga ulanganda chaqiriladi."""
        await websocket.accept()
        if chat_id not in self.active_connections:
            self.active_connections[chat_id] = []
        self.active_connections[chat_id].append(websocket)

    def disconnect(self, websocket: WebSocket, chat_id: int):
        """Foydalanuvchi chatdan chiqqanda yoki aloqa uzilganda."""
        if chat_id in self.active_connections:
            if websocket in self.active_connections[chat_id]:
                self.active_connections[chat_id].remove(websocket)
            # Agar chatda hech kim qolmasa, xotirani bo'shatamiz
            if not self.active_connections[chat_id]:
                del self.active_connections[chat_id]

    async def broadcast(self, message: dict, chat_id: int):
        """Ma'lum bir chatdagi barcha aktiv foydalanuvchilarga ma'lumot yuboradi."""
        if chat_id in self.active_connections:
            for connection in self.active_connections[chat_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    # Agar ulanish yopiq bo'lsa, xatolik bermasligi uchun
                    pass

manager = ConnectionManager()
