# import asyncio
# import asyncpg
# import logging
# from config import DB_CONFIG
#
# async def fix():
#     logging.basicConfig(level=logging.INFO)
#     try:
#         conn = await asyncpg.connect(**DB_CONFIG)
#         logging.info("Baza bilan aloqa o'rnatildi.")
#
#         migrations = [
#             "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user';",
#             "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);",
#             "ALTER TABLE users ADD COLUMN IF NOT EXISTS address TEXT;",
#             "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_online BOOLEAN DEFAULT FALSE;",
#             "ALTER TABLE users ADD COLUMN IF NOT EXISTS lat DOUBLE PRECISION;",
#             "ALTER TABLE users ADD COLUMN IF NOT EXISTS lon DOUBLE PRECISION;",
#             "ALTER TABLE users ADD COLUMN IF NOT EXISTS balance DECIMAL(12, 2) DEFAULT 0.00;",
#             "ALTER TABLE users ADD COLUMN IF NOT EXISTS language_code VARCHAR(10) DEFAULT 'uz';",
#             "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
#         ]
#
#         for mig in migrations:
#             try:
#                 await conn.execute(mig)
#                 logging.info(f"Muvaffaqiyatli: {mig}")
#             except Exception as e:
#                 logging.error(f"Xatolik ({mig}): {e}")
#
#         await conn.close()
#         logging.info("Baza muvaffaqiyatli yangilandi.")
#     except Exception as e:
#         logging.error(f"Ulanishda xatolik: {e}")
#
# if __name__ == "__main__":
#     asyncio.run(fix())
