import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
API_KEY=os.getenv('API_KEY')

client = genai.Client(api_key=API_KEY)
MODEL_NAME = "gemini-flash-latest"

SYSTEM_INSTRUCTION = """
Siz Logistika_bot loyihasining maxsus yordamchisisiz. 
Sizning vazifalaringiz:
1. FAQAT logistika, yuk tashish, haydovchilik va transportga oid savollarga javob berish. 
2. Agar foydalanuvchi yuk yubormoqchi bo'lsa (matn yoki ovoz orqali), undan quyidagilarni ajratib oling:
   - Qayerdan (From)
   - Qayerga (To)
   - Yuk turi (Cargo Type)
   - Vazni (Weight)
   - Sana (Date) - ixtiyoriy
3. Agar ma'lumotlar to'liq bo'lsa, ularni chiroyli formatda "E'LON TAYYOR" deb xulosa qiling va foydalanuvchidan tasdiqlashni so'rang.
4. Agar ma'lumotlar yetarli bo'lmasa, yetishmayotgan ma'lumotlarni muloyimlik bilan so'rang.
5. Logistikaga aloqasi bo'lmagan savollarga: "Kechirasiz, men faqat logistika sohasida yordam bera olaman." deb javob bering.
6. Muloqot tilini foydalanuvchi tanlagan tilda (O'zbek yoki Rus) davom ettiring.
"""

# Database configuration
DB_CONFIG = {
    "user": os.getenv('USER', 'postgres'),
    "password": os.getenv('PASSWORD', 'postgres'),
    "database": os.getenv('DB', 'logistika_db'),
    "host": os.getenv('DB_HOST', "127.0.0.1"),
    "port": int(os.getenv('DB_PORT', 5432))
}

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set in .env file")
