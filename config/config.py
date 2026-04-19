import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from google import genai
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from passlib.context import CryptContext


load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
API_KEY = os.getenv('API_KEY')
WEBAPP_URL = os.getenv('WEBAPP_URL')

client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-flash-latest"

ADMIN_IDS: set[int] = {int(i.strip()) for i in os.getenv("ADMIN", "").split(",") if i.strip()}


def is_admin(user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
    return False


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



DATABASE_URL = os.getenv("DB_URL")

engine = create_async_engine(DATABASE_URL, echo=False)
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
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env file")

from dotenv import load_dotenv

load_dotenv()


import jwt
from datetime import datetime, timedelta, timezone

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict):
    """
    JWT token yaratadi.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt, expire