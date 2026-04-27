from fastapi import FastAPI
from config.config import engine,Base
# MUHIM: Barcha modellarni modul darajasida import qilish 
# (shunda ular registry'ga ro'yxatdan o'tadi va circular import bo'lmaydi)
import users.models
import driver.models
import order.models
import ai.models

from sqlalchemy.orm import configure_mappers
configure_mappers()

from driver.router import router as driver_router
from order.router import router as order_router
from ai.router import router as ai_router
from users.router import router as auth_router

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="FastAPI")

# Uploads papkasini yaratish va static qilib ulash
if not os.path.exists("uploads"):
    os.makedirs("uploads")
app.mount("/static/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app.include_router(driver_router, prefix="/api")
app.include_router(order_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])



