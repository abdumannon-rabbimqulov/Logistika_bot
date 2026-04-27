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
from users.router import router as auth_router

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="FastAPI")

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
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])



