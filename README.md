# Logistika Bot

Ushbu loyiha logistika sohasi uchun mo'ljallangan Telegram bot hisoblanadi. Bot orqali yuk beruvchilar va haydovchilar bir-birini topishi, e'lonlar qoldirishi va yuklarni yetkazib berish bo'yicha kelishuvlar amalga oshirishi ko'zda tutilgan.

## Loyiha Haqida

Botda 2 xil foydalanuvchi roli mavjud:
1. **Mijoz (Yuk beruvchi)** - Yuk jo'natish uchun buyurtmalar (Order) yaratadi, haydovchilardan keladigan takliflarni ko'rib chiqib qabul qiladi.
2. **Haydovchi** - Botdan ro'yxatdan o'tadi (mashinasi, raqami va ruxsatnomalari tasdiqlanadi). Mijozlar yaratgan buyurtmalarga taklif (Offer) qoldirishi yoki o'zlari ham yo'nalish bo'yicha e'lonlar (DriverAnnouncement) qoldirib mijozlardan takliflar olishi mumkin.

**Loyiha tuzilmasi:**
- `config/` - Loyihaning asosiy sozlamalari va ma'lumotlar bazasi bilan ishlash (`database.py`, `models.py`). Asosiy modellar (User, TruckType, Driver, Order, OrderOffer, DriverAnnouncement).
- `handlers/` - Foydalanuvchilar bilan bo'ladigan barcha o'zaro aloqani boshqaradigan qism (`start.py`, `order.py`, `driver_reg.py`, `menu.py`, `location.py`, `ai.py` va hokazo).
- `keyboards/` - Tugmalar (menyular, tasdiqlash va inkor etish tugmalari uchun).
- `middlewares/` - Botga kelayotgan xabarlarga ishlov berish uchun qo'shimcha mexanizmlar (masalan `i18n.py` til uchun, `logging.py` xabarlarni loglash uchun).
- `main.py` - Loyihaning kirish nuqtasi, botni va dispetcherni asinxron tarzda ishga tushiruvchi modul.

## Asosiy Texnologiyalar va Kutubxonalar

Loyihani yaratishda quyidagi asosiy kutubxonalar va freymvorklardan foydalanilgan:

* **aiogram (3.26.0)** - Asinxron Telegram bot yaratish uchun eng kuchli zamonaviy freymvork.
* **SQLAlchemy (2.0.49)** - Ma'lumotlar bazasi ustida ORM sifatida ishlash.
* **asyncpg (0.31.0)** - PostgreSQL bazasiga asinxron ulanish drayveri.
* **psycopg2-binary** - PostgreSQL uchun qo'shimcha ulanish sinxron va umumiy amallar uchun vosita.
* **google-generativeai / google-genai** - AI (Gemini va boshqalar) bilan ishlash, ehtimol xabarlarga intellektual tarzda ishlov berish (masofaviy dispatcher vazifasida).
* **pydantic** - Ma'lumotlarni validatsiya qilish.
* **python-dotenv** - Maxfiy ma'lumotlar (\`.env\`) faylidan xavfsiz foydalanish.

To'liq ro'yxati `requirements.txt` faylida keltirilgan (quyida eng asosiylari):
- aiohttp, aiofiles
- cryptography
- certifi
- grpcio
- tenacity

## Qanday Ishga Tushiriladi?

1. Loyiha papkasida `.env` faylini yarating va quyidagi turdagi o'zgaruvchilarni kiriting (masalan, `BOT_TOKEN`, `API_KEY` yoki DB uchun `DB_URL`).
2. Virtual muhitga kutubxonalarni o'rnating: `pip install -r requirements.txt`
3. Botni ishga tushiring: `python main.py`

# Sqlalchemyda migrations

````
alembic revision --autogenerate -m "initial"
````

# Sqlalchemy migrate
````
alembic upgrade head
````
