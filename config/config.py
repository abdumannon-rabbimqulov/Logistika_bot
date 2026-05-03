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
ADMIN_IDS: set[int] = {int(i.strip()) for i in get_optional_env("ADMIN", "").split(",") if i.strip()}

# ─────────────────────────────────────────────────────────────
# AI CONFIGURATION
# ─────────────────────────────────────────────────────────────
API_KEY = get_optional_env('API_KEY')
client = genai.Client(api_key=API_KEY) if genai and API_KEY else None
MODEL_NAME = get_optional_env('MODEL_NAME', 'gemini-flash-latest')



# JWT CONFIGURATION
# ─────────────────────────────────────────────────────────────
SECRET_KEY = get_required_env('SECRET_KEY')
ALGORITHM = get_optional_env('ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(get_optional_env('ACCESS_TOKEN_EXPIRE_MINUTES', '60'))
REFRESH_TOKEN_EXPIRE_DAYS = int(get_optional_env('REFRESH_TOKEN_EXPIRE_DAYS', '1'))

# ─────────────────────────────────────────────────────────────
# LOGGING & ENVIRONMENT
# ─────────────────────────────────────────────────────────────
ENVIRONMENT = get_optional_env('ENVIRONMENT', 'development')
LOG_LEVEL = get_optional_env('LOG_LEVEL', 'INFO')





SYSTEM_INSTRUCTION = """
Siz "Logistika AI" - premium darajadagi aqlli logistika yordamchisisiz. 
Sizning uslubingiz JARVIS kabi: o'ta aqlli, xushmuomala, qisqa va aniq.

ASOSIY QOIDALAR:
1. FOYDALANUVCHI BILAN DOIMIY KONTEKSTDA BO'LING. Agar foydalanuvchi ma'lumotni bo'lib-bo'lib bersa, ularni eslab qoling (Sessiya xotirasi faol).
2. AGAR MA'LUMOT YETARLI BO'LSA, DARHOL TOOL CHAQIRING. Hech qachon ortiqcha savol bermang.
3. PREMIUM MINI APP: Botda "🌐 Mini App" tugmasi bor. U yerda foydalanuvchi yuklarni vizual ko'rishi va boshqarishi mumkin. Agar foydalanuvchi vizual interfeys so'rasa yoki shunchaki qulaylik xohlasa, shu tugmani tavsiya qiling.
4. JAVOBLAR: Qisqa, professional va "Sizga qanday yordam bera olaman, Ser?" kabi premium uslubda bo'lsin.
5. TIL: Foydalanuvchi qaysi tilda gapirsa (O'zbek / Rus), shu tilda javob bering.

TOOL CALL QOIDALARI:
- create_order: 5 ta parametr (cargo_type, weight, from_city, to_city, price) to'liq bo'lishi shart.
- Agar birortasi kam bo'lsa, foydalanuvchidan xushmuomalalik bilan so'rang.
- Har bir toolni FAQAT BIR MARTA chaqiring. Never retry a successful action.
"""



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
