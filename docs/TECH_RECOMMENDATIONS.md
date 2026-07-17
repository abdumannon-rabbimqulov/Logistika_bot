# Texnik Tavsiyalar — Kerakli Qo'shimchalar va Texnologiyalar

> Holat: TAVSIYA (joriy holat uchun qarang: `docs/SYSTEM_DESIGN.md`)
> Avtomatik dispatch tizimiga oid texnologik qarorlar (APScheduler, matching engine, WebSocket push) allaqachon `docs/DISPATCH_SYSTEM_PLAN.md`da batafsil yozilgan — bu yerda **takrorlanmaydi**, faqat shu hujjatga havola beriladi.
> Sana: 2026-07-17

Ustuvorlik: 🔴 Kritik (production'ga xavf) · 🟡 Muhim (yaqin muddatda kerak) · ⚪ Kelajakda (masshtab oshganda)

---

## 1. 🔴 Ma'lumotlar bazasi migratsiyasi — Alembic'ni haqiqiy ishga tushirish

**Muammo:** `config/main.py:42` — `Base.metadata.create_all` orqali sxema yaratiladi. `alembic.ini` bor, lekin `migrations/versions/` papkasi umuman yo'q (faqat `env.py`). Production'da modelga ustun qo'shilsa (masalan `dispatch_attempts`), avtomatik `ALTER TABLE` bo'lmaydi — mavjud ma'lumot yo'qolish xavfi bilan qo'lda tuzatishga majbur bo'lasiz.

**Tavsiya:** `alembic revision --autogenerate` orqali joriy sxemani baseline migratsiya sifatida saqlash, `config/main.py`dagi `create_all` chaqiruvini olib tashlash, deploy jarayoniga `alembic upgrade head` qadamini qo'shish (Dockerfile `CMD` yoki `docker-compose` `entrypoint` skripti).

---

## 2. 🔴 Avtomatlashtirilgan testlar + CI

**Muammo:** Repo ichida faqat bitta qo'lda ishga tushiriladigan `test_ws.py` bor, `.github/workflows/` yo'q. `handlers/`, `Admin_panel/`, auth (`users/auth.py`) kabi kritik logika regressiyaga qarshi himoyasiz.

**Tavsiya:**
- **pytest + pytest-asyncio** — async endpoint/servis testlari uchun (loyiha to'liq async, bu tabiiy tanlov).
- **httpx.AsyncClient** (`ASGITransport`) — FastAPI endpointlarini haqiqiy server ko'tarmasdan sinash uchun.
- **pytest-postgresql** yoki test uchun alohida `docker-compose.test.yml` (mavjud PostGIS image bilan) — real DB'ga yaqin muhitda testlash (SQLite emas, chunki loyiha PostGIS-specific `Geometry` ustunlaridan foydalanadi).
- **GitHub Actions** (`.github/workflows/ci.yml`) — har PR'da: lint (`ruff`), testlar, va `alembic upgrade head --sql` orqali migratsiya validatsiyasi.

---

## 3. 🟡 Xatolik kuzatuvi (error tracking)

**Muammo:** `middlewares/error_handler.py` global xatoliklarni ushlaydi, lekin production'da xato qachon, qaysi userda, qaysi stack trace bilan yuz berganini ko'rish uchun markazlashgan joy yo'q — faqat log fayllar.

**Tavsiya:** **Sentry** (`sentry-sdk[fastapi]`) — bitta `sentry_sdk.init()` chaqiruvi bilan FastAPI va aiogram (ikkalasi ham, chunki ikkalasi alohida process) xatolarini avtomatik ushlaydi, `ENVIRONMENT` env'iga qarab release/tag ajratiladi. Self-hosted variant kerak bo'lsa — GlitchTip (Sentry protokoliga mos, ochiq kodli, yengilroq).

---

## 4. 🟡 Strukturaviy loglash

**Muammo:** `logging.basicConfig` (`main.py:21`) oddiy matnli format — production'da log agregatsiya (grep bilan qidirish) noqulay, `driver_id`/`order_id` kabi maydonlar bo'yicha filtrlash yo'q.

**Tavsiya:** **structlog** — JSON formatda, `bind()` orqali kontekst (masalan `order_id`, `driver_id`) avtomatik har log qatoriga qo'shiladi. Docker Compose'dagi konteyner loglarini keyin **Loki + Grafana** (yengil, self-hosted) yoki oddiy `docker logs` bilan ham o'qish mumkin bo'ladi.

---

## 5. 🟡 Bildirishnoma yuborish ishonchliligi

**Muammo:** `services/notifications.py` — `urllib.request` bilan sync HTTP so'rov (`asyncio.to_thread` orqali) Telegram Bot API'ga to'g'ridan-to'g'ri yuboriladi, aiogram Botning o'zidan foydalanilmaydi. Xato bo'lsa (Telegram 429 rate-limit, tarmoq xatosi) — faqat log yoziladi, qayta urinish yo'q, xabar butunlay yo'qoladi.

**Tavsiya:** `aiogram.Bot.send_message` (mavjud `handlers/bot.py`dagi `bot` instansidan foydalanish — API va bot bir xil kod bazasida bo'lsa import qilish mumkin, yoki botga alohida ichki HTTP endpoint/queue orqali). Qayta urinish uchun **tenacity** (`@retry(wait=wait_exponential(), stop=stop_after_attempt(3))`) — ayniqsa avtomatik dispatch tizimida (`DISPATCH_SYSTEM_PLAN.md`) bu **kritik**, chunki yo'qolgan bildirishnoma = haydovchiga yetib bormagan buyurtma taklifi.

---

## 6. 🟡 Region/tuman aniqligi — geografik FK

**Muammo:** `Driver.current_region`/`current_city` — erkin matn (`String`). "Toshkent" va "Toshkent shahri" SQL `WHERE`da mos kelmaydi, region-fallback matching (dispatch uchun ham, hozirgi qidiruv uchun ham) noaniq.

**Tavsiya:** `regions`/`districts` ma'lumotnoma jadvallari (`scripts/seed_uzbekistan_geo.py` allaqachon shunga o'xshash seed skripti — shu asosda kengaytirish), `Driver.current_region_id`/`current_district_id` FK, profil formada dropdown (erkin matn input emas). Bu `DISPATCH_SYSTEM_PLAN.md` 3.4-bo'limida ham qayd etilgan.

---

## 7. ⚪ Fayl saqlash — object storage

**Muammo:** Yuklangan rasmlar (`driver/router.py` — truck type rasmlari, haydovchi hujjatlari) local diskka (`uploads/`) yoziladi. Docker Compose bitta hostda ishlaganda muammo yo'q, lekin gorizontal scale (bir nechta `web` konteyner) yoki server almashtirilganda fayllar yo'qoladi.

**Tavsiya:** **MinIO** (S3-mos, self-hosted, Docker Compose'ga bitta xizmat sifatida qo'shiladi) yoki tayyor S3 (agar bulutga chiqilsa). `aiofiles` local yozish o'rniga `boto3`/`aioboto3` bilan upload — kod o'zgarishi minimal, chunki fayl nomi/URL patterni allaqachon bor.

---

## 8. ⚪ API rate limiting

**Muammo:** FastAPI endpointlarida (masalan `/auth/login`, AI chat) so'rov sonini cheklovchi middleware ko'rinmadi — brute-force yoki AI-limit chetlab o'tish xavfi (garchi `AI_DAILY_LIMIT_*` mavjud bo'lsa ham, bu daraja emas, minut/soniya darajasidagi himoya emas).

**Tavsiya:** **slowapi** (FastAPI uchun, Redis backend bilan — loyihada Redis allaqachon bor, qo'shimcha infra kerak emas) — `@limiter.limit("5/minute")` kabi dekorator, ayniqsa login va AI endpointlariga.

---

## 9. ⚪ Reverse proxy / TLS

**Muammo:** `docker-compose.yml`da `web` to'g'ridan-to'g'ri 8000-portda ochiq, `API_PUBLIC_PREFIX=/api` izohida "nginx /api/ prefiksini uzatadi" deyilgan — demak Nginx kutilmoqda, lekin repo ichida uning konfiguratsiyasi yo'q (tashqarida bo'lishi mumkin, tekshirish kerak).

**Tavsiya:** Agar hali yo'q bo'lsa — **Nginx** (yoki **Caddy**, avtomatik Let's Encrypt TLS bilan, konfiguratsiyasi soddaroq) `docker-compose.yml`ga xizmat sifatida qo'shilsin, WebSocket (`/ws/location`, kelajakdagi `/ws/dispatch`) uchun `proxy_set_header Upgrade`/`Connection` sozlamalari unutilmasin.

---

## Xulosa — ustuvorlik tartibida

| # | Tavsiya | Texnologiya | Ustuvorlik |
|---|---|---|---|
| 1 | Haqiqiy DB migratsiyalari | Alembic (mavjud, ishga tushirish kerak) | 🔴 |
| 2 | Test + CI | pytest-asyncio, httpx, GitHub Actions | 🔴 |
| 3 | Xatolik kuzatuvi | Sentry / GlitchTip | 🟡 |
| 4 | Strukturaviy loglash | structlog (+ Loki/Grafana ixtiyoriy) | 🟡 |
| 5 | Ishonchli bildirishnoma | aiogram Bot + tenacity retry | 🟡 |
| 6 | Region/tuman FK | `regions`/`districts` jadvallari | 🟡 |
| 7 | Object storage | MinIO (S3-mos) | ⚪ |
| 8 | Rate limiting | slowapi + Redis | ⚪ |
| 9 | Reverse proxy/TLS | Nginx yoki Caddy | ⚪ |
| — | Avtomatik dispatch (matching, timer, dual-channel push) | APScheduler + Redis, WebSocket — **batafsil:** `docs/DISPATCH_SYSTEM_PLAN.md` | — |
