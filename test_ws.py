import asyncio
import websockets
import json
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from config.config import SQLALCHEMY_DATABASE_URI
from auth.security import create_access_token
from users.models import User
from ai.models import Chat

engine = create_async_engine(SQLALCHEMY_DATABASE_URI)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def test_ws():
    async with async_session() as db:
        chat = (await db.execute(select(Chat).where(Chat.id == 5))).scalar_one_or_none()
        if not chat:
            print("Chat 5 not found!")
            return
        
        user_id = chat.user_id
        if not user_id:
            print("Chat has no user_id!")
            return
            
        print(f"Testing with user_id: {user_id}")
        token = create_access_token({"sub": str(user_id)})
        
    uri = f"ws://127.0.0.1:8000/api/ai/ws/5?token={token}"
    print("Connecting to:", uri)
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            await websocket.send(json.dumps({"type": "ping"}))
            response = await websocket.recv()
            print("Received:", response)
    except websockets.exceptions.ConnectionClosed as e:
        print(f"Connection closed: {e.code} - {e.reason}")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test_ws())
