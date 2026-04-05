import asyncpg
import logging
from config.config import DB_CONFIG

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        if not self.pool:
            try:
                self.pool = await asyncpg.create_pool(**DB_CONFIG)
                logging.info("✅ Ma'lumotlar bazasiga ulanish hovuzi yaratildi.")
            except Exception as e:
                logging.error(f"❌ Bazaga ulanishda xatolik: {e}")

    async def close(self):
        """Close the connection pool."""
        if self.pool:
            await self.pool.close()
            logging.info("Ma'lumotlar bazasiga ulanish hovuzi yopildi.")

    async def update_user_language(self, telegram_id, lang_code):
        """Update user language preference."""
        query = "UPDATE users SET language_code = $1 WHERE telegram_id = $2;"
        async with self.pool.acquire() as conn:
            await conn.execute(query, lang_code, telegram_id)

    async def get_user(self, telegram_id):
        """Get user by telegram_id."""
        query = "SELECT * FROM users WHERE telegram_id = $1;"
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, telegram_id)

    async def update_user_role(self, telegram_id, role):
        """Update user role (user/driver)."""
        query = "UPDATE users SET role = $1 WHERE telegram_id = $2;"
        async with self.pool.acquire() as conn:
            await conn.execute(query, role, telegram_id)

    async def add_driver(self, telegram_id, driver_data):
        """Add a vehicle for a driver."""
        user = await self.get_user(telegram_id)
        if not user:
            logging.error(f"Foydalanuvchi topilmadi: {telegram_id}")
            return

        query = """
                INSERT INTO driver (
                    telegram_id, 
                    type_car, 
                    country_number, 
                    dela_top, 
                    dela_back, 
                    load_weight, 
                    cont_length, 
                    passport_back, 
                    passport_top
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9);
            """
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(
                    query,
                    telegram_id,
                    driver_data.get('type_car'),
                    driver_data.get('country_number'),
                    driver_data.get('dela_top'),
                    driver_data.get('dela_back'),
                    driver_data.get('weight'),
                    driver_data.get('length'),
                    driver_data.get('pass_back'),
                    driver_data.get('pass_top')
                )
                return True
            except Exception as e:
                logging.error(f"Driver qo'shishda xatolik: {e}")
                return False


    async def add_user_to_db(self, telegram_id, full_name, username):
        """Add user to database with ON CONFLICT check."""
        if not self.pool:
            await self.connect()

        query = """
            INSERT INTO users (telegram_id, full_name, username)
            VALUES ($1, $2, $3)
            ON CONFLICT (telegram_id) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                username = EXCLUDED.username
            RETURNING *;
        """
        async with self.pool.acquire() as conn:
            try:
                user = await conn.fetchrow(query, telegram_id, full_name, username)
                return user
            except Exception as e:
                logging.error(f"Foydalanuvchini qo'shishda xatolik: {e}")
                return None

    async def update_location(self, telegram_id, lat, lon):

        yandex_url=f"https://yandex.uz/maps/?ll={lon}%2C{lat}&z=15&l=map&pt={lon}%2C{lat}"

        query = "UPDATE users SET address_url = $1 WHERE telegram_id = $2;"
        async with self.pool.acquire() as conn:
            try:
                await conn.execute(query, yandex_url, telegram_id)
                logging.info(f"📍 Manzil yangilandi: {telegram_id}")
                return True
            except Exception as e:
                logging.error(f"Manzilni yangilashda xatolik: {e}")
                return False


db = Database()