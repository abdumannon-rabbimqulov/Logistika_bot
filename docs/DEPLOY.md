# Serverga deploy

Toza Ubuntu serverda loyihani noldan ko'tarish va keyinchalik yangilab turish
qo'llanmasi. Butun stack Docker'da ishlaydi; tashqariga faqat **80** va **443**
portlari ochiladi, HTTPS sertifikatini Caddy avtomatik oladi.

Lokalda sinash uchun → [Lokal sinov](#lokal-sinov) bo'limiga o'ting.

---

## Arxitektura

```
Internet :80 / :443
      │
   [caddy]  ← Let's Encrypt sertifikati avtomatik olinadi va yangilanadi
      │  reverse_proxy frontend:80
      ▼
 [frontend]  nginx + `npm run build` bergan statik dist/
      ├── /                      → SPA (index.html)
      ├── /api/, /static/, WS    → web:8000
      ├── /support/              → support:8000
      └── /osrm/route/v1/...     → osrm:5000   (5 r/s, faqat GET, faqat `route`)
      
 [web] [bot] [dispatch-worker] [events-worker] [support]  — port ochmaydi
 [db] [logistika-redis] [rabbitmq] [osrm]                 — faqat 127.0.0.1
 [migrate]  — bir martalik: alembic upgrade head, keyin tugaydi
```

Frontend va API brauzer uchun **bitta origin**da (`https://DOMAIN`) — CORS
muammosi yo'q va Telegram Mini App talabiga (HTTPS) mos keladi.

---

## 1. Server tayyorlash

Minimal talab: 4 GB RAM, 2 vCPU, ~15 GB bo'sh joy (OSRM xaritasi ~1 GB +
qayta ishlangan fayllar).

```bash
# Docker Engine + compose plugin (Ubuntu)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"   # keyin qayta login qiling
docker compose version            # v2 ekanini tekshiring
```

### Portlarni yopish

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

> Postgres (5432), Redis (6380), RabbitMQ (5672/15672), OSRM va backend
> portlari `docker-compose.prod.yml` da allaqachon `127.0.0.1` ga bog'langan,
> ya'ni ufw'siz ham tashqaridan ko'rinmaydi. ufw ikkinchi himoya qatlami.

### DNS

`DOMAIN` uchun **A-yozuvi** server IP'siga yo'naltirilgan bo'lishi **shart** —
Caddy sertifikatni HTTP-01 tekshiruvi orqali oladi va domen server'ga
yo'naltirilmagan bo'lsa sertifikat berilmaydi.

```bash
dig +short yuk.example.uz   # server IP'sini qaytarishi kerak
```

---

## 2. Loyihani olish va sozlash

```bash
git clone <repo-url> /opt/logistika
cd /opt/logistika

cp .env.example .env
nano .env
```

`.env` da **albatta** to'ldiriladiganlar:

| O'zgaruvchi | Izoh |
|---|---|
| `BOT_TOKEN` | @BotFather bergan token |
| `SECRET_KEY` | JWT uchun uzun tasodifiy satr — `openssl rand -hex 32` |
| `DB_PASSWORD` | kuchli parol |
| `DB_URL` | `DB_PASSWORD` bilan **mos** bo'lsin (ikkalasida ham bir xil parol) |
| `DOMAIN` | masalan `yuk.example.uz` |
| `ACME_EMAIL` | sertifikat bildirishnomalari uchun pochta |
| `WEBAPP_URL` | `https://<DOMAIN>` — **https bo'lishi shart** |
| `CORS_ORIGINS` | `https://<DOMAIN>` |
| `RABBITMQ_PASSWORD` | standart `guest` ni **o'zgartiring** (`RABBITMQ_URL` ni ham) |
| `ADMIN` | admin Telegram ID(lar), vergul bilan |
| `API_YANDEX_KEY`, `API_KEY` | geokoder va AI kalitlari |

`ENVIRONMENT=production`, `VITE_API_BASE_URL=/api` — o'zgartirilmaydi.

`scripts/server-deploy.sh` bularning bo'sh yoki namunaviy (`change_me`,
`your_`, `example.org`) qolganini o'zi tekshiradi va deploy'ni to'xtatadi.

---

## 3. OSRM xaritasi (birinchi marta, ~1 GB)

Marshrut va masofa hisoblash shu ma'lumotga tayanadi. Xaritasiz `osrm`
konteyneri healthcheck'dan o'tmaydi, `web`/`bot`/`dispatch-worker` esa uni
`service_healthy` bilan kutgani uchun **umuman ishga tushmaydi**.

```bash
./scripts/update-osrm-map.sh     # yuklab olish + qayta ishlash, ancha vaqt oladi
ls -lh osrm-data/uzbekistan.osrm
```

---

## 4. Deploy

```bash
make deploy
```

Skript ketma-ket bajaradi: old shartlarni tekshirish → `.env` ni tekshirish →
OSRM xaritasi borligini tekshirish → `git pull` → image'larni yig'ish →
`up -d` → barcha healthcheck'lar `healthy` bo'lguncha kutish → `/health` ni
so'rash → eski image qatlamlarini tozalash.

Migratsiyalar alohida bir martalik `migrate` konteynerida bajariladi va
`web`/`bot`/worker'lar uning **muvaffaqiyatli tugashini** kutadi.

Tekshirish:

```bash
make prod-ps
BASE=https://yuk.example.uz make prod-smoke
```

Brauzerda `https://<DOMAIN>` ochiling, Telegram'da botga `/start` yuboring —
chat menyusida Mini App tugmasi paydo bo'lishi kerak.

---

## 5. Yangilash

```bash
cd /opt/logistika
make deploy
```

`make deploy` — idempotent, xohlagancha qayta ishga tushirish mumkin.

### Rollback

`server-deploy.sh` tugagach oldingi backend image ID'sini chop etadi:

```bash
docker tag <ESKI_IMAGE_ID> logistika_backend:latest
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-build
```

> Migratsiyalar avtomatik qaytarilmaydi. Sxemani o'zgartirgan relizni
> qaytarayotgan bo'lsangiz: `docker compose ... run --rm migrate \
> alembic downgrade -1`.

---

## 6. Zaxira nusxa

Yo'qotib bo'lmaydigan ikki narsa — **baza** va **yuklangan fayllar**:

```bash
# Baza (ikkala DB ham)
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db \
    pg_dumpall -U postgres | gzip > backup-$(date +%F).sql.gz

# Yuklangan fayllar (uploads_data volume)
docker run --rm -v logistika_bot_uploads_data:/data -v "$PWD:/out" alpine \
    tar czf /out/uploads-$(date +%F).tar.gz -C /data .
```

> Volume nomining prefiksi compose loyihasi nomidan (papka nomi) kelib chiqadi.
> Aniq nomni `docker volume ls` bilan tekshiring.

Tiklash:

```bash
gunzip -c backup-2026-08-09.sql.gz | \
    docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db psql -U postgres
```

`caddy_data` volume'ida sertifikatlar saqlanadi — uni o'chirmang, Let's Encrypt
yangi sertifikat so'rovlariga haftalik limit qo'yadi.

---

## 7. Kuzatish va nosozliklarni bartaraf etish

```bash
make prod-logs                                   # hamma loglar
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f web
make prod-ps                                     # holat + ochiq portlar
```

Ichki panellarga kirish (portlar 127.0.0.1 da) — **kompyuteringizda**:

```bash
ssh -N -L 15672:localhost:15672 FOYDALANUVCHI@SERVER_IP   # RabbitMQ UI
ssh -N -L 8003:localhost:8003  FOYDALANUVCHI@SERVER_IP    # backend /docs
```

Monitoring (Netdata + Dockge) alohida stack: [docs/MONITORING.md](MONITORING.md).

### Tez-tez uchraydigan muammolar

| Alomat | Sabab va yechim |
|---|---|
| Domen ochilmaydi, `caddy` logida ACME xatosi | DNS A-yozuvi server IP'siga yo'naltirilmagan yoki 80-port yopiq. `dig +short <DOMAIN>` va `ufw status` ni tekshiring |
| `osrm` `starting` holatida qotib qolgan | `osrm-data/uzbekistan.osrm` yo'q yoki buzilgan → `./scripts/update-osrm-map.sh` |
| `web` ko'tarilmaydi, `migrate` yiqilgan | `docker compose ... logs migrate`. Ko'pincha `.env` dagi `DB_URL` parol `DB_PASSWORD` bilan mos emas |
| Telegram'da Mini App tugmasi yo'q | `.env` da `WEBAPP_URL` https emas. Tuzatib, `docker compose ... restart bot` |
| Buyurtma narxi hisoblanmaydi (503) | OSRM ishlamayapti → `docker compose ... ps osrm` |
| Rasm yuklanmaydi / ko'rinmaydi | `uploads_data` volume. `docker compose ... exec web ls -la /app/uploads` |
| ARM serverda OSRM juda sekin | `docker-compose.yml` dagi `osrm` xizmatidan `platform: linux/amd64` qatorini olib tashlang |
| Linux'da **dev** rejimda "Permission denied" (uploads) | Konteyner `app` (uid 10001) nomidan ishlaydi, bind-mount qilingan `./uploads` esa host foydalanuvchiniki. macOS'da Docker buni o'zi hal qiladi, Linux'da esa: `sudo chown -R 10001:10001 uploads`. Prod'da bunday muammo yo'q — u yerda named volume |

---

## Lokal sinov

Serverga chiqarishdan oldin **aynan o'sha prod stack**ni kompyuterda ko'tarish
mumkin. `DOMAIN=localhost` bo'lganda Caddy Let's Encrypt'ga umuman chiqmaydi —
o'zining ichki CA'si bilan sertifikat beradi.

```bash
make down          # dev stack bilan portlar urishmasin
make prod-local    # DOMAIN=localhost bilan to'liq prod stack
make prod-smoke    # tashqaridan tekshirish (curl)
```

So'ng:

* `https://localhost/` — SPA (brauzer sertifikatga ishonmaydi, "Advanced →
  Proceed" bosing yoki `curl -k` ishlating)
* `https://localhost/api/health` — backend

To'xtatish va dev rejimga qaytish:

```bash
make prod-down
make up
```

> Dev va prod bir xil volume'lardan (`postgres_data`, `redis_data`,
> `rabbitmq_data`) foydalanadi, ya'ni baza umumiy. `uploads` esa farq qiladi:
> dev'da host papkasi (`./uploads`), prod'da `uploads_data` volume.

### Dev va prod farqi

| | Dev (`make up`) | Prod (`make prod-up`) |
|---|---|---|
| Frontend | Vite dev server, HMR, `:5173` | nginx + statik `dist/`, port ochmaydi |
| Kod | host'dan bind-mount (`.:/app`) | image ichida, o'zgarmas |
| HTTPS | yo'q | Caddy, avtomatik sertifikat |
| Migratsiya | qo'lda (`make migrate`) | avtomatik (`migrate` xizmati) |
| Ochiq portlar | 5173, 8000, 5432, 6380, 5672, 15672, 5001, 8010 | faqat 80, 443 |
| `--reload` | bor (`docker-compose.override.yml`) | yo'q |
