#!/bin/sh
# Backend image'ining kirish nuqtasi (Dockerfile ENTRYPOINT).
#
# Odatda hech narsa qilmaydi — berilgan buyruqni (`uvicorn ...`, `python main.py`,
# `python -m workers.dispatch_worker`) shunchaki ishga tushiradi. FAQAT
# `RUN_MIGRATIONS=1` berilganda migratsiyalarni qo'llaydi; docker-compose.prod.yml
# da bu o'zgaruvchi faqat bir martalik `migrate` xizmatida bor, ya'ni bir necha
# konteyner bir vaqtda alembic ishga tushirib bir-biriga xalaqit bermaydi.
set -e

if [ "$RUN_MIGRATIONS" = "1" ]; then
    echo "[entrypoint] Migratsiyalar tekshirilmoqda..."

    # Baza tayyor bo'lguncha kutish. `depends_on: service_healthy` odatda yetarli,
    # lekin Postgres healthcheck'dan keyin ham bir necha soniya ulanishni rad
    # etishi mumkin (initdb skriptlari tugayotganda) — shuning uchun qayta urinish.
    i=0
    until python -c "
import asyncio, sys
from sqlalchemy.ext.asyncio import create_async_engine
from config.config import DATABASE_URL

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect():
        pass
    await engine.dispose()

asyncio.run(main())
" 2>/dev/null; do
        i=$((i + 1))
        if [ "$i" -ge 30 ]; then
            echo "[entrypoint] XATO: bazaga 60 soniya ichida ulanib bo'lmadi." >&2
            exit 1
        fi
        echo "[entrypoint] Baza hali tayyor emas, kutilmoqda ($i/30)..."
        sleep 2
    done

    # Bu loyihada sxema uzoq vaqt `Base.metadata.create_all` orqali yaratilgan
    # (config/main.py lifespan). Bunday bazada `alembic_version` jadvali yo'q, lekin
    # jadvallar bor — `alembic upgrade head` birinchi revizyadanoq "table already
    # exists" bilan yiqiladi. Shuning uchun avval holat aniqlanadi:
    #   - jadvallar bor, alembic_version yo'q  → `stamp head` (mavjud sxema joriy deb belgilanadi)
    #   - qolgan barcha holatlar (toza baza yoki allaqachon stamp qilingan) → `upgrade head`
    STATE=$(python -c "
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from config.config import DATABASE_URL

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        has_alembic = await conn.scalar(text(
            \"select to_regclass('public.alembic_version') is not null\"
        ))
        # PostGIS o'z xizmat jadvallarini (spatial_ref_sys) qo'shadi — ular
        # 'baza bo'sh emas' degani emas, shuning uchun hisobga olinmaydi.
        n_tables = await conn.scalar(text(
            \"select count(*) from information_schema.tables\"
            \" where table_schema='public' and table_name not in\"
            \" ('spatial_ref_sys','geography_columns','geometry_columns','alembic_version')\"
        ))
    await engine.dispose()
    print('STAMP' if (n_tables and not has_alembic) else 'UPGRADE')

asyncio.run(main())
")

    if [ "$STATE" = "STAMP" ]; then
        echo "[entrypoint] Mavjud sxema topildi, alembic_version yo'q → 'alembic stamp head'."
        alembic stamp head
    fi

    echo "[entrypoint] alembic upgrade head"
    alembic upgrade head
    echo "[entrypoint] Migratsiyalar tayyor."
fi

exec "$@"
