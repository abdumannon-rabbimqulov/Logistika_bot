# Mikroservizlar arxitekturasi: Manager roli, Support xizmati va RabbitMQ

Bu hujjat uch narsani tushuntiradi: tizim qanday qismlarga bo'lingan, menejer nima
qila oladi (va nimani ATAYLAB qila olmaydi), hamda hammasini lokalda bitta buyruq
bilan qanday ishga tushirib sinash mumkin.

---

## 1. Umumiy ko'rinish

```
                     ┌──────────────────── RabbitMQ ────────────────────┐
                     │  logistika.dispatch (direct) — haydovchi qidirish │
                     │  logistika.events   (topic)  — biznes hodisalari  │
                     └──────────────────────────────────────────────────┘
                        ▲              ▲   │                    │
             publish    │              │   │ consume            │ consume
        ┌───────────────┴──┐    ┌──────┴───┴─────┐    ┌─────────▼──────────┐
        │  web             │    │ dispatch-worker│    │ events-worker      │
        │  FastAPI monolit │    │ qidiruv jarayoni│   │ adminlarga xabar   │
        │  /orders /auth   │    └────────────────┘    └────────────────────┘
        │  /system /manager│
        └────────┬─────────┘         ┌───────────────────────────┐
                 │                   │ support  (FastAPI)        │
                 │                   │ /support/tickets          │
                 │                   │ + AMQP consumer (ichida)  │
                 │                   └────────────┬──────────────┘
                 │ asyncpg                        │ asyncpg
        ┌────────▼────────────────────────────────▼────────┐
        │ PostgreSQL:   logistika_db    |    support_db    │
        └──────────────────────────────────────────────────┘

        qo'shimcha: bot (aiogram), redis, osrm, frontend
```

### Xizmatlar

| Xizmat | Port | Vazifa |
|---|---|---|
| `web` | 8000 | Asosiy API: buyurtmalar, auth, admin (`/system`), menejer (`/manager`) |
| `support` | 8010 | **Yordam mikroservizi** — murojaatlar va yozishmalar |
| `dispatch-worker` | — | Haydovchi qidirish navbatini qayta ishlaydi (mavjud edi) |
| `events-worker` | — | Support hodisalarini adminlarga Telegram orqali yetkazadi |
| `bot` | — | aiogram Telegram bot |
| `db` | 5432 | PostgreSQL + PostGIS (`logistika_db` va `support_db`) |
| `rabbitmq` | 5672 / 15672 | Broker + boshqaruv UI |
| `logistika-redis` | 6380 | Live-location keshi, dispatch qulflari |
| `osrm` | 5001 | Marshrut hisoblash |
| `frontend` | 5173 | Vite dev server |

### Nega support alohida mikroserviz

`support` xizmati asosiy loyihaning **kodini ham, bazasini ham** ishlatmaydi:

- o'z image'i (`support_service/Dockerfile`) — ichiga faqat `support_service/` papkasi
  ko'chiriladi, ya'ni bexosdan `from order.models import ...` yozib bo'lmaydi;
- o'z bazasi — `support_db` (bir xil Postgres konteynerida, boshqa DATABASE);
- o'z bog'liqliklari — `support_service/requirements.txt` (aiogram, geoalchemy2,
  shapely kerak emas).

Asosiy tizim bilan bog'lanish faqat ikki nuqtada:

1. **Umumiy `SECRET_KEY`** — JWT ni mahalliy tekshirish uchun (HTTP so'rovsiz);
2. **RabbitMQ `logistika.events`** — hodisalar almashinuvi.

---

## 2. Manager roli

### Nima qila oladi

| Amal | Endpoint |
|---|---|
| Buyurtmalar ro'yxati | `GET /api/manager/orders` |
| Buyurtma tafsiloti | `GET /api/manager/orders/{id}` |
| **Holatni yangilash** | `PATCH /api/manager/orders/{id}/status` |
| Mos yuk mashinalari ro'yxati | `GET /api/manager/orders/{id}/available-trucks` |
| **Mashinani biriktirish** | `POST /api/manager/orders/{id}/assign-truck` |
| Murojaatlarni ko'rish/javob berish | `GET|POST /support/tickets...` (port 8010) |

### Nima qila OLMAYDI — moliya

Menejer moliyaviy ma'lumotning **hech qanday ko'rinishini** ololmaydi. Bu tasodifiy
emas, uch qavatda ta'minlangan:

1. **Endpoint qavati.** Barcha moliyaviy amallar `/system` ostida va
   `Admin_panel.validation.is_admin` bilan himoyalangan. U esa
   `users/permissions.py: is_admin_user()` ni chaqiradi — bu funksiya menejerni
   o'tkazmaydi. Ya'ni balans to'g'rilash, balans tarixi, komissiya foizi va narx
   sozlamalari menejer uchun **403**.
2. **Maydon qavati.** `/manager/...` javob sxemalari (`manager/schemas.py`) narx
   maydonlarini umuman e'lon qilmaydi — `Optional` qilib bo'sh qoldirilmagan, balki
   sxemada YO'Q, shuning uchun FastAPI ularni javobdan butunlay chiqarib tashlaydi.
3. **Umumiy endpointlar qavati.** `/orders/...` javoblari hamma rol uchun bitta
   sxemadan foydalanadi, shuning uchun menejer so'raganda javob
   `manager/schemas.py: strip_finance_fields()` bilan tozalanadi (ichma-ich
   obyektlardan ham).

Buni `tests/test_manager_permissions.py` va `tests/test_manager_finance_isolation.py`
qulflab turadi: kimdir kelajakda `is_admin_user` ga menejerni qo'shsa yoki menejer
sxemasiga `price` qo'shsa — testlar darhol yiqiladi.

### "Truck" nima uchun `driver_id` orqali biriktiriladi

Loyihada alohida `trucks` jadvali yo'q: yuk mashinasi haydovchi profilining bir
qismi (`drivers.truck_number`, `drivers.truck_type_id`, `drivers.truck_year`), va
buyurtmaga `orders.driver_id` biriktiriladi. Shuning uchun "mashinani biriktirish"
amalda o'sha mashinaning haydovchisini biriktirishdir. Menejer interfeysida esa
aynan **mashina** ko'rsatiladi: davlat raqami, turi, sig'imi, reytingi.

`GET /manager/orders/{id}/available-trucks` standart holatda buyurtmaning
`required_truck_type_id` iga mos, tasdiqlangan (`docs_verified`), bo'sh
(`is_available`) va bloklanmagan mashinalarni qaytaradi. Mos mashina topilmasa
`?any_truck_type=true` bilan boshqa turdagilarni ham ko'rish mumkin.

Biriktirish `services/dispatch.py: assign_driver_manually()` orqali ketadi — u
atomik yangilashni (`WHERE driver_id IS NULL`), ochiq takliflarni bekor qilishni va
haydovchi/sender'ga bildirishnomani birga bajaradi.

---

## 3. RabbitMQ hodisalari

`logistika.events` — **topic** exchange (mavjud `logistika.dispatch` esa *direct*
bo'lib qoladi va o'zgarmagan). Farqi: `dispatch` — "shu ishni bajar" degan VAZIFA,
`events` — "shunday bo'ldi" degan XABAR, uni nechta xizmat tinglashi oldindan
noma'lum.

```
logistika.events (topic, durable)
    ├── order.status_changed   ─┬→ support.order_events    → support xizmati
    ├── order.truck_assigned   ─┘
    ├── support.ticket_created ─┬→ support.notifications   → events-worker
    └── support.ticket_replied ─┘
```

Har bir xabar bir xil konvertda:

```json
{
  "event": "order.status_changed",
  "event_id": "0f2c…",
  "occurred_at": "2026-08-05T09:12:33+00:00",
  "data": { "order_id": 12, "old_status": "accepted", "new_status": "in_progress",
            "changed_by_user_id": 501, "changed_by_role": "manager" }
}
```

Oqim misoli:

1. Menejer buyurtma holatini `in_progress` ga o'zgartiradi.
2. `order/crud.py: update_order_status()` **commit'dan keyin**
   `order.status_changed` hodisasini yuboradi.
3. Support xizmati uni `support.order_events` navbatidan oladi va shu buyurtmaga
   oid **ochiq** murojaatlarga tizim izohini qo'shadi:
   *"Buyurtma #12 holati o'zgardi: haydovchi biriktirildi → yo'lda (manager)"*.
4. Teskari yo'nalish: foydalanuvchi murojaat yozsa, support
   `support.ticket_created` yuboradi, `events-worker` esa adminlarga Telegram
   xabarini beradi.

**Publish hech qachon so'rovni buzmaydi.** `publish_event()` barcha istisnolarni
yutadi va faqat logga yozadi: buyurtma holati allaqachon bazaga yozilgan, broker
o'chgani uchun foydalanuvchiga 500 qaytarish noto'g'ri bo'lardi.

---

## 4. JWT va rollar

Token endi `role` claim'ini ham olib yuradi:

```json
{ "sub": "501", "role": "manager", "type": "access", "exp": … }
```

- **Asosiy ilova** rolni HAMON bazadan o'qiydi (`users/auth.py: get_current_user`) —
  admin rolni o'zgartirsa yoki foydalanuvchi banlansa, eski token bilan eski
  huquqlar ishlab qolmaydi. Claim — qulaylik, manba haqiqat emas.
- **Support mikroservizi** esa asosiy bazaga ulanmagani uchun claim'ga tayanadi.
  Token muddati (60 daqiqa) eskirish oynasini cheklaydi, va bu xizmatda pulga yoki
  buyurtmaga ta'sir qiladigan amal yo'q.

Rol matritsasi bitta joyda — `users/permissions.py`:

| Rol | Huquqlar |
|---|---|
| `admin` | Hammasi, shu jumladan **moliya** (`/system`) |
| `manager` | Buyurtma holati + mashina biriktirish. **Moliya yo'q** |
| `sender` | O'z buyurtmalarini yaratish/tahrirlash, narxini boshqarish |
| `driver` | Taklifni qabul qilish, marshrut nuqtalarini belgilash |
| `guest` | Faqat `/auth/select-role` |

---

## 5. Ishga tushirish va sinash

### 5.1 Tayyorgarlik

```bash
cp .env.example .env
# .env da to'ldirilishi shart: BOT_TOKEN, SECRET_KEY, DB_PASSWORD, ADMIN
```

`SECRET_KEY` bitta bo'lishi muhim — `support` xizmati tokenni shu kalit bilan
tekshiradi.

### 5.2 Ishga tushirish

```bash
docker compose up --build
```

⚠️ **Muhim:** `support_db` bazasini yaratadigan skript
(`scripts/init-support-db.sh`) Postgres image'ining qoidasi bo'yicha FAQAT bo'sh
volume'da, ya'ni birinchi ishga tushishda bajariladi. Loyiha bazasi allaqachon
mavjud bo'lsa, bazani bir marta qo'lda yarating:

```bash
docker compose exec db psql -U postgres -c "CREATE DATABASE support_db"
docker compose restart support
```

(Yoki toza boshlash: `docker compose down -v && docker compose up --build` —
DIQQAT: bu barcha ma'lumotni o'chiradi.)

### 5.3 Sog'liq tekshiruvi

```bash
curl localhost:8000/health          # web       → {"status":"ok"}
curl localhost:8010/health          # support   → {"status":"ok","service":"support"}
open http://localhost:8000/docs     # asosiy API Swagger
open http://localhost:8010/docs     # support API Swagger
make mq-ui                          # RabbitMQ UI (guest/guest)
```

RabbitMQ UI → **Exchanges** da `logistika.events` (topic) va **Queues** da
`support.order_events`, `support.notifications` ko'rinishi kerak.

### 5.4 Migratsiya (menejer roli uchun SHART)

`manager` qiymati PostgreSQL `userrole` enum tipiga migratsiya orqali qo'shiladi:

```bash
make migrate        # = docker compose exec web alembic upgrade head

# tekshirish:
docker compose exec db psql -U postgres -d logistika_db \
  -c "SELECT unnest(enum_range(NULL::userrole))"
# ro'yxatda 'manager' bo'lishi kerak
```

### 5.5 Menejer yaratish

```bash
# 1) admin sifatida login
ADMIN_TOKEN=$(curl -s -X POST localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone_number":"+998901234567","password":"admin-parol"}' | jq -r .access_token)

# 2) mavjud foydalanuvchiga menejer rolini berish
curl -X PATCH localhost:8000/api/system/users/501 \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"role":"manager"}'

# 3) menejer sifatida login (tokenda role=manager bo'ladi)
MGR=$(curl -s -X POST localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone_number":"+998901112233","password":"menejer-parol"}' | jq -r .access_token)

# claim'ni ko'rish:
echo $MGR | cut -d. -f2 | base64 -d 2>/dev/null   # {"sub":"501","role":"manager",…}
```

### 5.6 Menejer huquqlarini sinash — **200 kutiladi**

```bash
# buyurtmalar (narx maydonlari YO'Q bo'lishi kerak)
curl -s -H "Authorization: Bearer $MGR" localhost:8000/api/manager/orders | jq

# mos mashinalar
curl -s -H "Authorization: Bearer $MGR" \
  localhost:8000/api/manager/orders/1/available-trucks | jq

# mashinani biriktirish
curl -s -X POST -H "Authorization: Bearer $MGR" -H 'Content-Type: application/json' \
  localhost:8000/api/manager/orders/1/assign-truck -d '{"driver_id":3}' | jq

# holatni yangilash
curl -s -X PATCH -H "Authorization: Bearer $MGR" -H 'Content-Type: application/json' \
  localhost:8000/api/manager/orders/1/status -d '{"status":"in_progress"}' | jq
```

### 5.7 Moliya bloki — **403 kutiladi**

```bash
curl -i -H "Authorization: Bearer $MGR" \
  localhost:8000/api/system/users/5/balance/transactions      # 403

curl -i -X POST -H "Authorization: Bearer $MGR" -H 'Content-Type: application/json' \
  localhost:8000/api/system/users/5/balance/adjust -d '{"amount":1000}'   # 403

curl -i -H "Authorization: Bearer $MGR" \
  localhost:8000/api/system/settings/commission               # 403
```

Maydon darajasini ham tekshiring — quyidagi buyruq **bo'sh** natija berishi kerak:

```bash
curl -s -H "Authorization: Bearer $MGR" localhost:8000/api/manager/orders/1 \
  | jq 'keys | map(select(. == "price" or . == "currency" or . == "base_price"))'
# []  ← narx maydonlari umuman yo'q
```

Taqqoslash uchun admin o'sha buyurtmani narxi bilan ko'radi:

```bash
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" localhost:8000/api/orders/1 | jq .price
```

### 5.8 RabbitMQ oqimini kuzatish

5.6 dagi holat o'zgarishidan keyin:

```bash
make support-logs | grep -i "order.status_changed"
# support xizmati hodisani oldi va murojaatlarga izoh qo'shdi
```

RabbitMQ UI → Queues → `support.order_events` da "Total" sanog'i oshadi.

### 5.9 Support mikroservizini sinash

```bash
# foydalanuvchi murojaat yaratadi
curl -s -X POST localhost:8010/support/tickets \
  -H "Authorization: Bearer $USER_TOKEN" -H 'Content-Type: application/json' \
  -d '{"subject":"Yuk kechikdi","body":"Haydovchi 3 soat kech keldi","order_id":1,"priority":"high"}' | jq

# menejer/admin HAMMA murojaatni ko'radi
curl -s -H "Authorization: Bearer $MGR" localhost:8010/support/tickets | jq

# javob yozish (murojaat avtomatik in_progress ga o'tadi)
curl -s -X POST localhost:8010/support/tickets/1/messages \
  -H "Authorization: Bearer $MGR" -H 'Content-Type: application/json' \
  -d '{"body":"Tekshiryapmiz, uzr so'raymiz."}' | jq

# holatni yopish (faqat xodim)
curl -s -X PATCH localhost:8010/support/tickets/1/status \
  -H "Authorization: Bearer $MGR" -H 'Content-Type: application/json' \
  -d '{"status":"resolved"}' | jq

# adminlarga bildirishnoma ketganini ko'rish
make events-logs
```

Buyurtma holati o'zgargandan keyin murojaatni qayta oching — ichida
`is_system: true` bo'lgan avtomatik izoh paydo bo'ladi:

```bash
curl -s -H "Authorization: Bearer $MGR" localhost:8010/support/tickets/1 \
  | jq '.messages[] | select(.is_system)'
```

### 5.10 Testlar

```bash
make test          # = docker compose exec web pytest tests/ -q
```

Yoki host'da: `pytest tests/ -q`. Testlar baza yoki broker talab qilmaydi.

---

## 6. Foydali `make` buyruqlari

| Buyruq | Vazifa |
|---|---|
| `make up` | Butun stack |
| `make migrate` | Alembic migratsiyalari |
| `make test` | Unit testlar |
| `make mq-ui` | RabbitMQ boshqaruv paneli |
| `make support-logs` | Support xizmati loglari |
| `make support-ui` | Support Swagger UI |
| `make support-db` | `support_db` ga psql bilan kirish |
| `make events-logs` | Bildirishnoma worker'i loglari |
| `make worker-scale n=3` | Dispatch worker'lar sonini oshirish |

---

## 7. Fayllar xaritasi

| Yo'l | Nima |
|---|---|
| `users/permissions.py` | **Rol matritsasining yagona joyi** (RBAC) |
| `manager/router.py`, `manager/schemas.py` | Menejer paneli va narxsiz sxemalar |
| `services/queue.py` | RabbitMQ: dispatch vazifalari + `logistika.events` |
| `workers/events_worker.py` | Support hodisalari → adminlarga Telegram |
| `support_service/` | **Mustaqil mikroserviz** (o'z DB, image, requirements) |
| `scripts/init-support-db.sh` | `support_db` bazasini yaratadi |
| `migrations/versions/b2f7c1a94d03_manager_role.py` | `userrole` enum'iga `manager` |
| `tests/test_manager_permissions.py` | Moliya bloki qulfi (rol darajasi) |
| `tests/test_manager_finance_isolation.py` | Moliya bloki qulfi (maydon darajasi) |
| `tests/test_event_contract.py` | Xizmatlararo hodisa shartnomasi |
