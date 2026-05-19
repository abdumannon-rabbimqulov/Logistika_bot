# Logistika AI API — To'liq Dokumentatsiya

**Version:** 1.0.0  
**Base URL (Production):** `https://logistic.org.uz/api`  
**Base URL (Local):** `http://localhost:8003`  
**OpenAPI (Swagger):** `/docs`  
**ReDoc:** `/redoc`

---

## Mundarija

- [Autentifikatsiya](#autentifikatsiya)
- [System](#system-endpointlari)
- [Auth](#auth-endpointlari)
- [Drivers](#drivers-endpointlari)
- [Orders](#orders-endpointlari)
- [AI & Chat](#ai--chat-endpointlari)
- [Admin — System](#admin--system-endpointlari)
- [Admin — AI](#admin--ai-endpointlari)
- [Admin — Tariff Payments](#admin--tariff-payments-endpointlari)
- [WebSocket](#websocket-endpointlari)
- [Xato kodlari](#xato-kodlari)
- [Postman](#postman-kolleksiyasi)

---

## Autentifikatsiya

API JWT (JSON Web Token) autentifikatsiyadan foydalanadi.

### Token olish

```
POST /auth/login
```

### Header format

```
Authorization: Bearer <access_token>
```

### Token turlari

| Token | Muddati | Tavsif |
|-------|---------|--------|
| Access Token | 60 daqiqa | API so'rovlari uchun |
| Refresh Token | 1 kun | Yangi tokenlar olish uchun |

### Login usullari

1. **Telefon + parol** — `phone_number` va `password`
2. **Telegram Web App** — `init_data` (HMAC-SHA256 bilan tekshiriladi)

### Foydalanuvchi rollari

| Rol | Tavsif |
|-----|--------|
| `guest` | Ro'yxatdan o'tmagan |
| `sender` | Yuk jo'natuvchi (mijoz) |
| `driver` | Haydovchi |
| `admin` | Administrator |

---

## System endpointlari

### `GET /` — API kirish nuqtasi

Autentifikatsiya talab qilinmaydi.

**Javob:**
```json
{
    "service": "Logistika AI API",
    "api_base": "/api",
    "docs": "/api/docs",
    "health": "/api/health"
}
```

### `GET /health` — Sog'lik tekshiruvi

**Javob:**
```json
{
    "status": "ok",
    "service": "Logistika AI API",
    "environment": "production",
    "timestamp": "2026-05-19T12:00:00+00:00"
}
```

### `GET /health/db` — Database tekshiruvi

**Javob:**
```json
{
    "status": "ok",
    "database": "connected"
}
```

---

## Auth endpointlari

**Prefix:** `/auth`

### `POST /auth/login` — Tizimga kirish

**Auth:** Yo'q

**Body (telefon + parol):**
```json
{
    "phone_number": "+998901234567",
    "password": "parol12345"
}
```

**Body (Telegram):**
```json
{
    "init_data": "query_id=AAHdF6IQ...&hash=abc123..."
}
```

**Javob (200):**
```json
{
    "access_token": "eyJhbGci...",
    "refresh_token": "eyJhbGci...",
    "role": "sender",
    "user_id": 123456789
}
```

**Haydovchi profili to'liq bo'lmasa (200):**
```json
{
    "access_token": "...",
    "refresh_token": "...",
    "role": "driver",
    "user_id": 123,
    "status": "need_driver_profile",
    "message": "Haydovchi rolini tanlagansiz, lekin profil ma'lumotlaringiz to'liq emas."
}
```

---

### `POST /auth/refresh` — Tokenlarni yangilash

**Auth:** Yo'q

**Body:**
```json
{
    "refresh_token": "eyJhbGci..."
}
```

**Javob (200):**
```json
{
    "access_token": "yangi_access_token",
    "refresh_token": "yangi_refresh_token",
    "token_type": "bearer"
}
```

---

### `POST /auth/reset-phone` — Parol tiklash (kod yuborish)

**Auth:** Yo'q

**Body:**
```json
{
    "phone_number": "+998901234567"
}
```

**Javob (200):**
```json
{
    "detail": "Tasdiqlash kodi Telegram akkauntingizga yuborildi.",
    "access_token": "eyJhbGci..."
}
```

---

### `POST /auth/verify-reset-code` — Kodni tekshirish

**Auth:** Bearer (reset-phone dan olingan token)

**Body:**
```json
{
    "code": "123456"
}
```

---

### `POST /auth/reset-password` — Yangi parol o'rnatish

**Auth:** Bearer

**Body:**
```json
{
    "new_password": "yangiparol123",
    "confirm_password": "yangiparol123"
}
```

> Parol 8-20 belgi oralig'ida bo'lishi kerak.

---

### `GET /auth/me` — Profil ko'rish

**Auth:** Bearer

**Javob (200):**
```json
{
    "id": 123456789,
    "username": "foydalanuvchi",
    "full_name": "Ism Familiya",
    "email": null,
    "phone_number": "+998901234567",
    "role": "sender",
    "language": "uz",
    "is_active": true,
    "is_banned": false,
    "balance": "0.00",
    "created_at": "2026-01-15T10:30:00",
    "updated_at": "2026-05-19T08:00:00"
}
```

---

### `PATCH /auth/me` — Profilni yangilash

**Auth:** Bearer

**Body:**
```json
{
    "full_name": "Yangi Ism",
    "phone_number": "+998991234567",
    "language": "uz"
}
```

---

### `PATCH /auth/me/password` — Parolni o'zgartirish

**Auth:** Bearer

**Body:**
```json
{
    "old_password": "eskiparol123",
    "new_password": "yangiparol123"
}
```

---

### `DELETE /auth/me` — Akkauntni deaktivatsiya qilish

**Auth:** Bearer

**Javob (200):**
```json
{
    "detail": "Akkaunt muvaffaqiyatli deaktivatsiya qilindi."
}
```

---

### `POST /auth/logout` — Chiqish

**Auth:** Bearer

**Body:**
```json
{
    "refresh_token": "eyJhbGci..."
}
```

> Refresh token Redis orqali qora ro'yxatga tushadi.

---

## Drivers endpointlari

**Prefix:** `/drivers`

### Mashina turlari (Truck Types)

#### `GET /drivers/truck-types` — Barcha mashina turlari

**Auth:** Yo'q

**Javob (200):**
```json
[
    {
        "id": 1,
        "name": "Tentli fura",
        "max_weight": "20000",
        "max_volume": "86",
        "length": "13.6",
        "width": "2.45",
        "height": "2.7",
        "pallet_capacity": 33,
        "image_url": "/static/uploads/truck_type_xxx.jpg",
        "description": "Standart tentli yuk mashinasi",
        "is_active": true,
        "created_at": "2026-01-01T00:00:00"
    }
]
```

#### `GET /drivers/truck-types/{pk}` — Bitta mashina turi

**Auth:** Yo'q

#### `POST /drivers/truck-types` — Yangi mashina turi (Admin)

**Auth:** Bearer (Admin)

**Body:**
```json
{
    "name": "Tentli fura",
    "max_weight": 20000,
    "max_volume": 86,
    "length": 13.6,
    "width": 2.45,
    "height": 2.7,
    "pallet_capacity": 33,
    "description": "Standart tentli yuk mashinasi",
    "is_active": true
}
```

#### `PATCH /drivers/truck-types/{pk}` — Mashina turini yangilash (Admin)

**Auth:** Bearer (Admin)

#### `DELETE /drivers/truck-types/{pk}` — Mashina turini o'chirish (Admin)

**Auth:** Bearer (Admin)  
**Javob:** 204 No Content

#### `POST /drivers/truck-types/image` — Rasm yuklash (Admin)

**Auth:** Bearer (Admin)  
**Content-Type:** multipart/form-data

| Parametr | Tur | Tavsif |
|----------|-----|--------|
| `file` | File | Rasm (jpg, jpeg, png, webp, gif) |

**Javob (200):**
```json
{
    "url": "/static/uploads/truck_type_uuid.jpg",
    "filename": "original_name.jpg"
}
```

---

### Haydovchi profili

#### `POST /drivers/profile` — Profil yaratish

**Auth:** Bearer

**Body:**
```json
{
    "truck_type_id": 2,
    "truck_number": "10Z123ZZ",
    "truck_year": 2021,
    "current_city": "Namangan",
    "current_region": "Namangan viloyati",
    "phone_number": "+998901112233"
}
```

**Javob (201):**
```json
{
    "id": 1,
    "user_id": 123456789,
    "truck_type_id": 2,
    "truck_number": "10Z123ZZ",
    "truck_year": 2021,
    "current_city": "Namangan",
    "current_region": "Namangan viloyati",
    "rating": "0.00",
    "total_trips": 0,
    "cancel_count": 0,
    "on_time_percent": "0.00",
    "is_available": true,
    "is_blocked": false,
    "block_reason": null,
    "created_at": "2026-05-19T12:00:00",
    "updated_at": "2026-05-19T12:00:00"
}
```

#### `GET /drivers/me` — Mening profilim

**Auth:** Bearer

#### `PATCH /drivers/me` — Profilni yangilash

**Auth:** Bearer

**Body:**
```json
{
    "truck_number": "01A777BB",
    "current_city": "Toshkent",
    "is_available": true
}
```

---

### Safar e'lonlari (Announcements)

#### `POST /drivers/announcements` — E'lon berish

**Auth:** Bearer

**Body:**
```json
{
    "price": 3000000,
    "currency": "UZS",
    "available_weight": 20.0,
    "available_volume": 80.0,
    "departure_date": "2026-06-01T08:00:00Z",
    "description": "Katta fura, bo'sh joy bor",
    "driver_id": 5,
    "waypoints": [
        {
            "sequence": 1,
            "waypoint_type": "origin",
            "city": "Xiva"
        },
        {
            "sequence": 2,
            "waypoint_type": "destination",
            "city": "Toshkent"
        }
    ]
}
```

**Waypoint turlari:** `origin`, `destination`, `transit`  
**E'lon statuslari:** `active`, `filled`, `expired`, `cancelled`

#### `GET /drivers/announcements` — E'lonlar ro'yxati

**Auth:** Bearer  
**Query:** `?driver_id=5` (ixtiyoriy)

#### `GET /drivers/announcements/{pk}` — E'lon tafsilotlari

**Auth:** Bearer

#### `POST /drivers/announcements/{id}/offers` — E'longa taklif berish

**Auth:** Bearer

**Body:**
```json
{
    "cargo_name": "Mebel",
    "cargo_description": "Uy mebellar to'plami",
    "cargo_weight": 5.0,
    "cargo_volume": 20.0,
    "pickup_city": "Xiva",
    "delivery_city": "Toshkent",
    "offered_price": 2500000,
    "currency": "UZS",
    "comment": "Ehtiyotkorlik bilan tashish kerak"
}
```

#### `GET /drivers/announcements/{id}/offers` — E'lon takliflari

**Auth:** Bearer (faqat e'lon egasi)

#### `PATCH /drivers/offers/{pk}` — Taklifni yangilash

**Auth:** Bearer (faqat e'lon egasi)

**Body:**
```json
{
    "counter_price": 2700000,
    "counter_comment": "2.7 mln ga rozi bo'laman",
    "status": "accepted"
}
```

**Taklif statuslari:** `pending`, `seen`, `accepted`, `rejected`, `cancelled`, `expired`, `outbid`

---

## Orders endpointlari

**Prefix:** `/orders`

### `POST /orders/` — Buyurtma yaratish

**Auth:** Bearer

**Body:**
```json
{
    "cargo_name": "Qurilish mollari (sement)",
    "weight": 20.0,
    "volume": 30.0,
    "required_truck_type_id": 2,
    "price": 4500000,
    "currency": "UZS",
    "waypoints": [
        {
            "sequence": 1,
            "waypoint_type": "pickup",
            "address": "Toshkent, Sergeli sanoat zonasi",
            "contact_name": "Aziz",
            "contact_phone": "+998901112233"
        },
        {
            "sequence": 2,
            "waypoint_type": "delivery",
            "address": "Samarqand, Shahar markazi",
            "contact_name": "Jasur",
            "contact_phone": "+998934445566"
        }
    ]
}
```

> `customer_id` JWT tokendan avtomatik olinadi.

**Buyurtma statuslari:** `pending`, `accepted`, `in_progress`, `completed`, `cancelled`  
**Waypoint turlari:** `pickup`, `delivery`, `transit`  
**Waypoint statuslari:** `pending`, `arrived`, `completed`, `skipped`

### `GET /orders/` — Buyurtmalar ro'yxati

**Auth:** Bearer  
**Query parametrlari:**

| Parametr | Tur | Tavsif |
|----------|-----|--------|
| `customer_id` | int | Mijoz bo'yicha filtr |
| `driver_id` | int | Haydovchi bo'yicha filtr |
| `status` | string | Status bo'yicha filtr |

### `GET /orders/{pk}` — Buyurtma tafsilotlari

**Auth:** Bearer

### `PATCH /orders/{pk}` — Buyurtmani yangilash

**Auth:** Bearer (faqat buyurtma egasi)

**Body:**
```json
{
    "cargo_name": "Yangilangan yuk nomi",
    "price": 5000000,
    "status": "accepted"
}
```

### `DELETE /orders/{pk}` — Buyurtmani o'chirish

**Auth:** Bearer (faqat buyurtma egasi)  
**Javob:** 204 No Content

### `POST /orders/{order_id}/offers` — Buyurtmaga taklif berish

**Auth:** Bearer (faqat haydovchilar)

**Body:**
```json
{
    "offered_price": 4000000,
    "currency": "UZS",
    "estimated_pickup_time": "2026-06-01T10:00:00Z",
    "estimated_delivery_time": "2026-06-02T08:00:00Z",
    "comment": "Ertaga olib ketaman"
}
```

### `GET /orders/{order_id}/offers` — Takliflar ro'yxati

**Auth:** Bearer (faqat buyurtma egasi)

### `PATCH /orders/offers/{pk}` — Taklifni yangilash

**Auth:** Bearer

**Body:**
```json
{
    "counter_price": 4200000,
    "counter_comment": "Narxni bir oz ko'taramiz",
    "status": "accepted"
}
```

---

## AI & Chat endpointlari

**Prefix:** `/ai`

### AI yordamchi

#### `POST /ai/assistant/message` — AI ga savol

**Auth:** Bearer

**Body:**
```json
{
    "message": "Mening buyurtmalarimni ko'rsat",
    "chat_id": null
}
```

> `chat_id` bo'sh bo'lsa yangi/mavjud AI chat ochiladi.

**Javob (200):**
```json
{
    "reply": "Sizning 3 ta buyurtmangiz mavjud...",
    "chat_id": 15,
    "used_today": 5,
    "daily_limit": 50,
    "allowed": true
}
```

#### `GET /ai/assistant/chat` — AI chatini olish

**Auth:** Bearer

#### `GET /ai/assistant/messages` — AI chat xabarlari

**Auth:** Bearer  
**Query:** `?chat_id=1&limit=50&before_id=100`

---

### Peer chat (foydalanuvchilar o'rtasida)

#### `POST /ai/chats` — Chat yaratish

**Auth:** Bearer

**Body:**
```json
{
    "category": "conversation",
    "title": "Haydovchi bilan suhbat"
}
```

**Kategoriyalar:** `complaint`, `suggestion`, `conversation`, `ai_command`, `support`  
**Statuslar:** `open`, `resolved`, `pending`, `escalated`

#### `GET /ai/chats` — Mening chatlarim

**Auth:** Bearer

#### `GET /ai/chats/{chat_id}` — Chat tafsilotlari

**Auth:** Bearer

#### `GET /ai/chats/{chat_id}/messages` — Chat xabarlari

**Auth:** Bearer  
**Query:** `?limit=50&before_id=100`

#### `PATCH /ai/messages/{message_id}` — Xabarni tahrirlash

**Auth:** Bearer (faqat o'z xabari)

**Body:**
```json
{
    "content": "Tahrirlangan xabar matni"
}
```

#### `DELETE /ai/messages/{message_id}` — Xabarni o'chirish

**Auth:** Bearer (faqat o'z xabari)

---

### Media va baho

#### `POST /ai/upload` — Media yuklash

**Auth:** Bearer  
**Content-Type:** multipart/form-data

| Parametr | Tur | Tavsif |
|----------|-----|--------|
| `file` | File | Rasm, video, audio yoki dokument |

**Javob (200):**
```json
{
    "url": "/static/uploads/uuid.jpg",
    "filename": "original_name.jpg"
}
```

#### `POST /ai/ratings` — Baho berish

**Auth:** Bearer

**Body:**
```json
{
    "order_id": 1,
    "target_type": "driver",
    "target_driver": 1,
    "score": 5,
    "comment": "Juda yaxshi xizmat!",
    "criteria_scores": {
        "speed": 5,
        "safety": 5,
        "communication": 4
    }
}
```

> `score`: 1-5 orasida. `target_type`: `user` yoki `driver`.

#### `GET /ai/me/usage` — AI sarflari

**Auth:** Bearer

**Javob (200):**
```json
{
    "allowed": true,
    "used_today": 5,
    "daily_limit": 50
}
```

---

## Admin — System endpointlari

**Prefix:** `/system`  
**Auth:** Bearer (Admin roli yoki ADMIN_IDS ro'yxatida)

### `GET /system/dashboard/stats` — Dashboard statistikasi

**Javob (200):**
```json
{
    "users_total": 150,
    "users_today": 5,
    "drivers_total": 30,
    "drivers_online": 12,
    "drivers_live_gps": 8,
    "orders_total": 500,
    "orders_today": 15,
    "orders_by_status": {
        "pending": 10,
        "accepted": 5,
        "in_progress": 3,
        "completed": 480,
        "cancelled": 2
    },
    "offers_today": 25,
    "ai_requests_today": 100,
    "ai_input_tokens_today": 50000,
    "ai_output_tokens_today": 30000,
    "orders_last_7_days": [
        {"date": "2026-05-13", "count": 20},
        {"date": "2026-05-14", "count": 18}
    ]
}
```

### `GET /system/users` — Foydalanuvchilar

**Query:**

| Parametr | Tur | Tavsif |
|----------|-----|--------|
| `role` | string | admin, sender, driver, guest |
| `is_banned` | bool | Banlangan foydalanuvchilar |
| `is_active` | bool | Aktiv foydalanuvchilar |
| `search` | string | Ism/telefon bo'yicha qidiruv |
| `skip` | int | Offset (default: 0) |
| `limit` | int | Limit (1-200, default: 50) |

**Response header:** `X-Total-Count` — jami foydalanuvchilar soni

### `GET /system/users/{user_id}` — Foydalanuvchi tafsilotlari

### `PATCH /system/users/{user_id}` — Foydalanuvchini yangilash

**Body:**
```json
{
    "role": "driver",
    "is_banned": false,
    "is_active": true,
    "language": "uz",
    "full_name": "Yangilangan Ism"
}
```

### `DELETE /system/users/{user_id}` — Foydalanuvchini deaktivatsiya qilish

**Javob:** 204 No Content

### `GET /system/orders` — Barcha buyurtmalar

**Query:** `?status=pending&customer_id=1&driver_id=2&date_from=2026-01-01&date_to=2026-12-31&skip=0&limit=50`

### `GET /system/orders/{order_id}` — Buyurtma tafsilotlari

### `PATCH /system/orders/{order_id}` — Buyurtmani yangilash

**Body:**
```json
{
    "status": "cancelled",
    "description": "Admin tomonidan bekor qilindi"
}
```

### `DELETE /system/orders/{order_id}` — Buyurtmani o'chirish

### `GET /system/ai/commands` — AI buyruqlari logi

**Query:** `?user_id=1&status=success&command_type=find_order&skip=0&limit=50`

### `GET /system/drivers/locations` — Online haydovchilar lokatsiyalari

### `GET /system/drivers/{driver_id}/location` — Haydovchi lokatsiyasi

---

## Admin — AI endpointlari

**Prefix:** `/ai/admin`  
**Auth:** Bearer (Admin)

### `GET /ai/admin/settings` — AI sozlamalari

**Javob (200):**
```json
{
    "current_model": "gemini-flash-latest",
    "available_models": ["gemini-flash-latest", "gemini-pro"],
    "free_daily_limit": 50,
    "pro_daily_limit": 500,
    "default_model_env": "gemini-flash-latest"
}
```

### `GET /ai/admin/models` — Mavjud modellar

### `GET /ai/admin/model` — Joriy model

### `POST /ai/admin/model` — Modelni almashtirish

**Body:**
```json
{
    "model_name": "gemini-flash-latest"
}
```

### `PATCH /ai/admin/users/{user_id}/limit` — Foydalanuvchi AI limitini sozlash

**Body:**
```json
{
    "daily_requests": 100
}
```

### `PATCH /ai/admin/users/{user_id}/tariff` — Tarifni sozlash

**Body:**
```json
{
    "tariff": "pro"
}
```

> `tariff`: `free` yoki `pro`

### `GET /ai/admin/usage` — AI sarflari statistikasi

**Query:** `?user_id=1&date_from=2026-01-01&date_to=2026-12-31`

**Javob (200):**
```json
{
    "items": [
        {
            "user_id": 123,
            "usage_date": "2026-05-19",
            "requests": 25,
            "input_tokens": 12000,
            "output_tokens": 8000
        }
    ],
    "total_requests": 25,
    "total_input_tokens": 12000,
    "total_output_tokens": 8000
}
```

---

## Admin — Tariff Payments endpointlari

**Prefix:** `/system/tariffs`  
**Auth:** Bearer (Admin)

### `POST /system/tariffs/payments` — To'lov qo'shish

**Body:**
```json
{
    "user_id": 123,
    "billing_year": 2026,
    "billing_month": 5,
    "amount": 150000,
    "currency": "UZS",
    "tariff_code": "pro",
    "note": "May oyi uchun to'lov"
}
```

### `GET /system/tariffs/payments/all` — Barcha to'lovlar

**Query:** `?user_id=123&skip=0&limit=50`

### `GET /system/tariffs/payments/{payment_id}` — To'lov tafsilotlari

### `PATCH /system/tariffs/payments/{payment_id}` — To'lovni yangilash

### `DELETE /system/tariffs/payments/{payment_id}` — To'lovni o'chirish

### `GET /system/tariffs/users/{user_id}/payments` — Foydalanuvchi to'lovlari

**Query:** `?year=2026`

### `GET /system/tariffs/users/{user_id}/summary` — Oylik yig'indi

**Query:** `?year=2026` (majburiy)

**Javob (200):**
```json
[
    {
        "billing_month": "2026-05-01",
        "total_amount": "300000",
        "payment_count": 2,
        "currency": "UZS"
    }
]
```

---

## WebSocket endpointlari

### Peer Chat WebSocket

**URL:** `wss://logistic.org.uz/api/ai/ws/{chat_id}?token=ACCESS_TOKEN`

**Ulanish:** Token query parameter orqali yuboriladi.

**Yuborish mumkin bo'lgan hodisalar:**
```json
{"type": "ping"}
{"type": "new_message", "content": "Salom!"}
```

**Qabul qilinadigan hodisalar:**
```json
{"event": "connected", "data": {"chat_id": 1, "messages": []}}
{"event": "pong"}
{"event": "new_message", "data": {"id": 1, "content": "...", "sender_id": 123}}
{"event": "message_edited", "data": {"id": 1, "content": "yangi matn"}}
{"event": "message_deleted", "message_id": 1}
{"event": "error", "message": "Xatolik matni"}
```

**Xato kodlari:**
| Kod | Tavsif |
|-----|--------|
| 1008 | Yaroqsiz token / ruxsat yo'q / AI chat (REST ishlating) |

> AI chat uchun WebSocket ishlatilmaydi — `POST /ai/assistant/message` ishlating.

---

### Admin Driver Location Stream

**URL:** `wss://logistic.org.uz/api/system/drivers/locations/stream?token=ADMIN_ACCESS_TOKEN`

**Qabul qilinadigan hodisalar:**
```json
{"event": "snapshot", "items": [...]}
{"event": "update", "item": {"driver_id": 1, "lat": 41.3, "lon": 69.3, "ts": "..."}}
```

**Xato kodlari:**
| Kod | Tavsif |
|-----|--------|
| 4401 | Token yaroqsiz yoki yo'q |
| 4403 | Admin huquqi yo'q |

---

## Xato kodlari

| HTTP Status | Tavsif |
|-------------|--------|
| 200 | Muvaffaqiyatli |
| 201 | Yaratildi |
| 204 | O'chirildi (bo'sh javob) |
| 400 | Noto'g'ri so'rov (validation xatosi) |
| 401 | Autentifikatsiya xatosi (token yaroqsiz/yo'q) |
| 403 | Ruxsat yo'q (role/ownership tekshiruvi) |
| 404 | Topilmadi |
| 409 | Ziddiyat (masalan, telefon raqam allaqachon mavjud) |
| 422 | Validation xatosi (Pydantic) |
| 500 | Server xatosi |

**Xato javob formati:**
```json
{
    "detail": "Xato haqida tushuntirish matni"
}
```

---

## Postman kolleksiyasi

### Import qilish

1. Postman dasturini oching
2. **Import** tugmasini bosing
3. `postman/` papkasidagi fayllarni tanlang:
   - `Logistika_API.postman_collection.json` — to'liq API kolleksiyasi
   - `Logistika_API.postman_environment.json` — production muhiti
   - `Logistika_API_Local.postman_environment.json` — lokal muhit

### Environment o'zgaruvchilari

| O'zgaruvchi | Tavsif | Default |
|-------------|--------|---------|
| `baseUrl` | API base URL | `https://logistic.org.uz/api` |
| `accessToken` | JWT access token | Login dan avtomatik o'rnatiladi |
| `refreshToken` | JWT refresh token | Login dan avtomatik o'rnatiladi |
| `userId` | Joriy user ID | Login dan avtomatik o'rnatiladi |
| `userRole` | Foydalanuvchi roli | Login dan avtomatik o'rnatiladi |
| `truckTypeId` | Mashina turi ID | `1` |
| `driverId` | Haydovchi ID | `1` |
| `orderId` | Buyurtma ID | `1` |
| `announcementId` | E'lon ID | `1` |
| `offerId` | Taklif ID | `1` |
| `chatId` | Chat ID | `1` |
| `messageId` | Xabar ID | `1` |
| `targetUserId` | Maqsadli user ID (admin) | `1` |
| `paymentId` | To'lov ID | `1` |

### Avtomatik tokenlar

Login so'rovida **Tests** skripti mavjud — muvaffaqiyatli login dan so'ng `accessToken`, `refreshToken`, `userId`, `userRole` avtomatik saqlanadi.

### Ishlatish tartibi

1. Environment tanlang (Production yoki Local)
2. `Auth > Login` so'rovini yuboring — tokenlar avtomatik saqlanadi
3. Boshqa so'rovlarni yuboring — `Authorization: Bearer` avtomatik qo'shiladi
4. Token muddati tugasa `Auth > Refresh Token` yuboring
