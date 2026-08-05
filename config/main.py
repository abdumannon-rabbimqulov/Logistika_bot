import logging
from contextlib import asynccontextmanager



from config import registry
from fastapi import FastAPI
from config.config import (
    engine,
    UPLOAD_DIR,
    STATIC_PATH,
    ENVIRONMENT,
    API_PUBLIC_PREFIX,
    WEBAPP_URL,
    CORS_ORIGINS,
)
from config.registry import Base
from middlewares.error_handler import setup_error_handlers
import driver.models
import order.models
import order.dispatch_models
import users.models

from sqlalchemy.orm import configure_mappers
configure_mappers()

from driver.router import router as driver_router
from order.router import router as order_router
from users.router import router as auth_router
from Admin_panel.router import router as admin_router
from manager.router import router as manager_router

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: jadval sxemasini yaratish (production'da alembic migratsiyasi tavsiya etiladi).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Navbat topologiyasi (dispatch vazifalari + `logistika.events` biznes hodisalari)
    # shu yerda ham e'lon qilinadi: worker/support'dan oldin ko'tarilsa ham birinchi
    # publish yo'qolmasin. Broker hali tayyor bo'lmasa API baribir ishlayveradi —
    # publish paytida qayta uriniladi.
    from services import queue as dispatch_queue

    try:
        await dispatch_queue.declare_topology()
    except dispatch_queue.QueueUnavailable:
        logger.warning("RabbitMQ hozircha mavjud emas — navbat birinchi so'rovda ulanadi")

    yield

    # Shutdown: RabbitMQ va Redis ulanishlarini yopish.
    #
    # DIQQAT: dispatch sweep loop'i endi bu yerda EMAS — u `workers/dispatch_worker.py`
    # ga ko'chirildi. Web jarayoni sof API bo'lib qoldi, fon ishlari worker'da.
    from services.live_location import close_redis

    await dispatch_queue.close_queue()
    await close_redis()


_docs_prefix = API_PUBLIC_PREFIX or ""
app = FastAPI(
    title="Logistika AI API",
    version="1.0.0",
    description="🚀 Logistics platform with AI-powered order management",
    lifespan=lifespan,
    servers=[
        {"url": API_PUBLIC_PREFIX or "http://127.0.0.1:8003", "description": "API base (/api)"},
        {"url": "", "description": "Prefiksiz (localhost:8003)"},
    ],
    docs_url=f"{_docs_prefix}/docs" if _docs_prefix else "/docs",
    redoc_url=f"{_docs_prefix}/redoc" if _docs_prefix else "/redoc",
    openapi_url=f"{_docs_prefix}/openapi.json" if _docs_prefix else "/openapi.json",
)

# ─────────────────────────────────────────────────────────────
# Setup global error handlers
# ─────────────────────────────────────────────────────────────
setup_error_handlers(app)

# Uploads papkasini static qilib ulash
app.mount(STATIC_PATH, StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or [WEBAPP_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def _register_api_routers(
    target: FastAPI,
    *,
    prefix: str = "",
    include_in_schema: bool = True,
) -> None:
    kwargs = {"prefix": prefix, "include_in_schema": include_in_schema}
    target.include_router(driver_router, **kwargs)
    target.include_router(order_router, **kwargs)
    auth_prefix = f"{prefix}/auth".replace("//", "/")
    target.include_router(
        auth_router,
        prefix=auth_prefix,
        tags=["Auth"],
        include_in_schema=include_in_schema,
    )
    target.include_router(admin_router, **kwargs)
    # `/manager` — moliyasiz operativ panel. `/system` (admin, moliya) dan ATAYLAB
    # alohida router: menejerga admin endpointlaridan birortasi ham ochilmasligi kerak.
    target.include_router(manager_router, **kwargs)


_register_api_routers(app)
# Nginx /api/ → backend (prefix olib tashlanadi) va to'g'ridan-to'g'ri :8003/api/... uchun
_register_api_routers(app, prefix=API_PUBLIC_PREFIX, include_in_schema=False)


@app.get("/", tags=["System"], summary="API kirish nuqtasi")
@app.get(API_PUBLIC_PREFIX, tags=["System"], include_in_schema=False)
@app.get(f"{API_PUBLIC_PREFIX}/", tags=["System"], include_in_schema=False)
async def api_root():
    """Postman uchun: barcha endpointlar {API_PUBLIC_PREFIX} ostida chaqiriladi."""
    return {
        "service": "Logistika AI API",
        "api_base": API_PUBLIC_PREFIX,
        "docs": f"{API_PUBLIC_PREFIX}/docs",
        "health": f"{API_PUBLIC_PREFIX}/health",
        "examples": {
            "truck_types": f"{API_PUBLIC_PREFIX}/drivers/truck-types",
            "login": f"{API_PUBLIC_PREFIX}/auth/login",
        },
        "webapp_url": WEBAPP_URL,
    }





# ─────────────────────────────────────────────────────────────
# HEALTH CHECK & STATUS ENDPOINTS
# ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"], summary="Service health status")
@app.get(f"{API_PUBLIC_PREFIX}/health", tags=["System"], include_in_schema=False)
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
@app.get(f"{API_PUBLIC_PREFIX}/health/db", tags=["System"], include_in_schema=False)
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




