# Logistika Bot (Backend)

Bu repository backend uchun: FastAPI API + Telegram bot + Postgres/Redis.

`Frontend_bot` alohida repository sifatida deploy qilinadi va bu repoga aralashmaydi.

## Arxitektura (qisqa)

- Backend API: `backend-api` (`:8003`)
- Telegram bot: `backend-bot`
- Migrations: `migrations`
- DB: `db` (Postgres)
- Cache: `logistika-redis` (Redis)

## Muhim qoida

- Backend deploy: shu repository (`./deploy-all.sh`)
- Frontend deploy: `Frontend_bot` repository (`./deploy.sh`)
- Public Nginx asosiy configini frontend repo boshqaradi.

## .env tayyorlash

1. `.env` fayl yarating:
```bash
cp .env.example .env
```
2. Kamida quyilarni to'ldiring:
- `BOT_TOKEN`
- `SECRET_KEY`
- `API_KEY` (ixtiyoriy, AI ishlatilsa)
- `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- `ADMIN`
- `WEBAPP_URL=https://logistic.org.uz/drivers/`

## Deploy (serverga kirmasdan)

Lokal kompyuterdan:
```bash
cd /Users/user/Logistika_bot
./deploy-all.sh
```

Skript avtomatik:
- kodni serverga yuboradi;
- serverda backend docker servislarni rebuild/restart qiladi.

### Qo'shimcha flaglar

- Nginx configini backend tomondan majburan qo'yish:
```bash
LOGISTIKA_APPLY_NGINX=1 ./deploy-all.sh
```

- SSH kalit yo'li boshqacha bo'lsa:
```bash
LOGISTIKA_SSH_KEY=/path/to/key ./deploy-all.sh
```

- Server host o'zgarsa:
```bash
LOGISTIKA_SSH_HOST=root@SERVER_IP ./deploy-all.sh
```

## Deploy (server ichidan)

```bash
cd /root/Logistika_bot
git pull
LOGISTIKA_DEPLOY_LOCAL=1 ./deploy-all.sh
```

## Faqat backend containerlar

```bash
docker compose up -d --build db logistika-redis migrations backend-api backend-bot
```

## Tez tekshiruv

```bash
docker ps
curl http://127.0.0.1:8003/health
```

## Ko'p uchraydigan xatolar

- `PermissionError: /app/logs/app.log`
  - Logging fallback qo'shilgan: file yozolmasa console ga tushadi.
  - Backendni qayta build qiling: `docker compose up -d --build backend-api backend-bot`

- `502 Bad Gateway` (`/auth/login`)
  - Odatda backend container yiqilgan bo'ladi yoki `:8003` ishlamaydi.
  - `docker ps` va backend loglarni tekshiring.

## Migrations

```bash
alembic revision --autogenerate -m "message"
alembic upgrade head
```
