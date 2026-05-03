from fastapi import FastAPI
from config.config import engine, Base, UPLOAD_DIR, STATIC_PATH, LOG_LEVEL, ENVIRONMENT
from middlewares.error_handler import setup_error_handlers, setup_logging
import driver.models
import order.models
import ai.models
import users.models

# ─────────────────────────────────────────────────────────────
# Setup logging va error handlers
# ─────────────────────────────────────────────────────────────
setup_logging(environment=ENVIRONMENT)

from sqlalchemy.orm import configure_mappers
configure_mappers()

from driver.router import router as driver_router
from order.router import router as order_router
from ai.router import router as ai_router
from users.router import router as auth_router

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(
    title="Logistika AI API",
    version="1.0.0",
    description="🚀 Logistics platform with AI-powered order management"
)

# ─────────────────────────────────────────────────────────────
# Setup global error handlers
# ─────────────────────────────────────────────────────────────
setup_error_handlers(app)

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





# ─────────────────────────────────────────────────────────────
# HEALTH CHECK & STATUS ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"], summary="Service health status")
async def health_check():
    """Service ishlayaptimi tekshirish."""
    from datetime import datetime, timezone
    return {
        "status": "ok",
        "service": "Logistika AI API",
        "environment": ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/health/db", tags=["System"], summary="Database connection status")
async def db_health():
    """Database ulanishini tekshirish."""
    try:
        async with engine.begin() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e)
        }


@app.get("/api", tags=["Documentation"], summary="API documentation")
async def api_docs():
    """API dokumentatsiyasi va mavjud endpoints."""
    return {
        "title": "Logistika AI API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "endpoints": {
            "auth": "/api/auth",
            "drivers": "/api/driver",
            "orders": "/api/order",
            "ai": "/api/ai",
        },
        "health": {
            "status": "/health",
            "database": "/health/db"
        }
    }



