import os
import logging
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

try:
    from google import genai
except ImportError:
    genai = None

# Setup logging
logger = logging.getLogger(__name__)

# Load .env file
load_dotenv()


def get_required_env(key: str, default: str | None = None) -> str:
    """Get environment variable with validation."""
    value = os.getenv(key, default)
    if not value:
        error_msg = f"❌ CRITICAL: Environment variable '{key}' is not set. Check .env file or set it manually."
        logger.error(error_msg)
        raise ValueError(error_msg)
    return value


def get_optional_env(key: str, default: str | None = None) -> str | None:
    """Get optional environment variable."""
    return os.getenv(key, default)


# ─────────────────────────────────────────────────────────────
# BOT & WEB CONFIGURATION
# ─────────────────────────────────────────────────────────────
BOT_TOKEN = get_required_env('BOT_TOKEN')
WEBAPP_URL = get_optional_env('WEBAPP_URL', 'http://localhost:8000')
# Tashqi domen orqali API (Postman, Swagger): https://logistic.org.uz/api/...
API_PUBLIC_PREFIX = (get_optional_env("API_PUBLIC_PREFIX", "/api") or "/api").rstrip("/") or "/api"
ADMIN_IDS: set[int] = {int(i.strip()) for i in get_optional_env("ADMIN", "").split(",") if i.strip()}

# ─────────────────────────────────────────────────────────────
# AI CONFIGURATION
# ─────────────────────────────────────────────────────────────
API_KEY = get_optional_env('API_KEY')
client = genai.Client(api_key=API_KEY) if genai and API_KEY else None
MODEL_NAME = get_optional_env('MODEL_NAME', 'gemini-flash-latest')
AI_DAILY_LIMIT_FREE = int(get_optional_env("AI_DAILY_LIMIT_FREE", "50"))
AI_DAILY_LIMIT_PRO = int(get_optional_env("AI_DAILY_LIMIT_PRO", "500"))



# JWT CONFIGURATION
# ─────────────────────────────────────────────────────────────
SECRET_KEY = get_required_env('SECRET_KEY')
ALGORITHM = get_optional_env('ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(get_optional_env('ACCESS_TOKEN_EXPIRE_MINUTES', '60'))
REFRESH_TOKEN_EXPIRE_DAYS = int(get_optional_env('REFRESH_TOKEN_EXPIRE_DAYS', '1'))

# ─────────────────────────────────────────────────────────────
# REDIS CONFIGURATION
# ─────────────────────────────────────────────────────────────
REDIS_HOST = get_optional_env('REDIS_HOST', 'logistika_redis')
REDIS_PORT = int(get_optional_env('REDIS_PORT', '6379'))
REDIS_DB = int(get_optional_env('REDIS_DB', '2'))

# ─────────────────────────────────────────────────────────────
# DRIVER LIVE LOCATION
# ─────────────────────────────────────────────────────────────
LIVE_LOC_TTL_SEC = int(get_optional_env("LIVE_LOC_TTL_SEC", "120"))
LIVE_LOC_DB_THROTTLE_SEC = int(get_optional_env("LIVE_LOC_DB_THROTTLE_SEC", "60"))
LIVE_LOC_DEFAULT_PERIOD_SEC = int(get_optional_env("LIVE_LOC_DEFAULT_PERIOD_SEC", "1800"))

# ─────────────────────────────────────────────────────────────
# LOGGING & ENVIRONMENT
# ─────────────────────────────────────────────────────────────
ENVIRONMENT = get_optional_env('ENVIRONMENT', 'development')
LOG_LEVEL = get_optional_env('LOG_LEVEL', 'INFO')





SYSTEM_INSTRUCTION_BASE = """
Siz "Logistika AI" — logistika platformasining aqlli yordamchisisiz.
Uslubingiz: professional, qisqa, aniq, premium.

QOIDALAR:
1. KONTEKST: Suhbatdagi oldingi ma'lumotlarni eslang.
2. TOOL CHAQIRISH: Agar ma'lumot yetarli bo'lsa, darhol tegishli tool ni chaqiring. Ortiqcha tasdiq so'ramang. Muvaffaqiyatli bo'lsa qaytarib chaqirmang.
3. KAMCHILIK: Yetishmagan ma'lumotni xushmuomalalik bilan so'rang.
4. RUXSAT: O'z roleingizdan tashqaridagi amallarni rad qiling va sababini tushuntiring.
5. MINI APP: "Mini App" tugmasi orqali vizual interfeys mavjud — kerak bo'lsa tavsiya qiling.
"""

ROLE_INSTRUCTIONS = {
    "sender": (
        "Roleingiz — YUK BERUVCHI (mijoz). "
        "Buyurtma yarating, takliflarni boshqaring, haydovchining safar e'lonlariga taklif yuboring, "
        "haydovchini baholang. Boshqa rolelar uchun mo'ljallangan amallarni bajara olmaysiz."
    ),
    "driver": (
        "Roleingiz — HAYDOVCHI. "
        "Mavjud buyurtmalarni toping va taklif bering, o'z safar e'lonlaringizni yarating va boshqaring, "
        "kelgan takliflarni qabul yoki rad eting, GPS ni yangilang, mijozni baholang."
    ),
    "admin": (
        "Roleingiz — ADMIN. Hamma amallar mavjud, jumladan token statistikasi, "
        "foydalanuvchi limitini sozlash va AI model boshqaruvi."
    ),
    "guest": (
        "Roleingiz — GUEST. Avval ro'yxatdan o'ting va rol tanlang (sender yoki driver). "
        "Shundagina to'liq xizmatlardan foydalana olasiz."
    ),
}

LANG_DIRECTIVE = {
    "uz":      "Javobingiz har doim O'zbekcha (Lotin yozuvida) bo'lsin.",
    "uz_cyrl": "Жавобингиз ҳар доим Ўзбекча (Кирилл ёзувида) бўлсин.",
    "ru":      "Ваши ответы должны быть всегда на русском языке.",
}

# Default model — Redis/DB'da override qilinishi mumkin
DEFAULT_AI_DAILY_LIMIT = int(get_optional_env("AI_DAILY_LIMIT", "50"))

# Admin tomonidan tanlash mumkin bo'lgan model'lar
AVAILABLE_AI_MODELS = [
    "gemini-flash-latest",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
]



DATABASE_URL = get_required_env("DB_URL")

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_size=10, max_overflow=20)
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass



async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
STATIC_PATH = "/static/uploads"

if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

logger.info(f"✅ Configuration loaded successfully. Environment: {ENVIRONMENT}")
