# ── Build bosqichi ──────────────────────────────────────────────────────────
# Kompilyator va header'lar FAQAT shu yerda kerak: asyncpg, psycopg2, shapely
# kabi paketlar C kengaytmalarini shu bosqichda yig'adi. Ular tayyor image'ga
# tushmaydi — natijada yakuniy image ~300 MB kichrayadi va hujum sathi torayadi
# (ishlab turgan konteynerda gcc bo'lmaydi).
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# Virtual muhitga o'rnatiladi — keyingi bosqichga bitta papka sifatida ko'chiriladi.
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ── Ishga tushirish bosqichi ────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# `libpq5` — psycopg2 uchun ish vaqtidagi kutubxona (libpq-dev EMAS, u faqat build uchun).
# `curl` — HEALTHCHECK uchun. `tini` — PID 1 sifatida signal va zombi jarayonlarni
# to'g'ri boshqaradi: `docker compose stop` da uvicorn/aiogram SIGTERM ni haqiqatan
# oladi va navbatdagi xabarni ack qilib ulguradi.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Root bo'lmagan foydalanuvchi. `uploads/` ni oldindan yaratib egalik beramiz —
# prod'da u yerga named volume ulanadi va Docker bo'sh volume uchun huquqlarni
# aynan shu papkadan meros qiladi (aks holda konteyner fayl yoza olmasdi).
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/uploads \
    && chown -R app:app /app

COPY --chown=app:app . .

USER app

EXPOSE 8000

# HEALTHCHECK ATAYLAB bu yerda emas: bitta image'dan `web` (HTTP server), `bot`
# (aiogram polling) va worker'lar (RabbitMQ iste'molchilari) ishlaydi — 8000-portni
# faqat `web` ochadi. Image darajasidagi tekshiruv qolgan hammasini "unhealthy" deb
# belgilardi. Shuning uchun healthcheck xizmat darajasida, faqat `web` ga
# beriladi (docker-compose.prod.yml).

# Entrypoint odatda hech narsa qilmaydi va `command:` ni shundayligicha ishga
# tushiradi; RUN_MIGRATIONS=1 bo'lgandagina alembic'ni qo'llaydi.
ENTRYPOINT ["/usr/bin/tini", "--", "/app/scripts/docker-entrypoint.sh"]
CMD ["uvicorn", "config.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-config", "config/uvicorn_logging.json"]
