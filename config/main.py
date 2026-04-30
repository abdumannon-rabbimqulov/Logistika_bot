from fastapi import FastAPI
from config.config import engine, Base, UPLOAD_DIR, STATIC_PATH
import driver.models
import order.models
import ai.models
import users.models

from sqlalchemy.orm import configure_mappers
configure_mappers()

from driver.router import router as driver_router
from order.router import router as order_router
from ai.router import router as ai_router
from users.router import router as auth_router

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="Logistika AI API")

# Uploads papkasini static qilib ulash
app.mount(STATIC_PATH, StaticFiles(directory=UPLOAD_DIR), name="uploads")

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

app.include_router(driver_router)
app.include_router(order_router)
app.include_router(ai_router)
app.include_router(auth_router, prefix="/auth", tags=["Auth"])



