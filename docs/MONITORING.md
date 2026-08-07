# Monitoring — Netdata + Dockge

Serverdagi holatni real vaqtda kuzatish: CPU/RAM/disk/tarmoq, har bir Docker
konteynerining resurs iste'moli, PostgreSQL / Redis / RabbitMQ metrikalari va
muammo yuz berganda Telegram'ga avtomatik xabar.

| Nima | Vazifasi | RAM |
|---|---|---|
| **Netdata** | Kuzatish: grafiklar, tarix, alertlar | ~100 MB |
| **Dockge** | Boshqarish: konteyner restart, jonli log | ~50 MB |

Ikkalasi ham `docker-compose.monitoring.yml` da — **alohida stack**. Bu ataylab:
monitoring ilova bilan birga yiqilib qolmasligi kerak, aynan o'shanda kerak bo'ladi.

Konfiguratsiya `monitoring/netdata/` da, git'da saqlanadi. Serverda hech narsani
qo'lda tahrirlash shart emas — `git pull` + `make mon-up` yetadi.

---

## Nega aynan shu yechim

`apt` bilan host'ga o'rnatish o'rniga konteyner tanlandi: sozlamalar git'da qoladi,
serverni qayta o'rnatganda hech narsa yo'qolmaydi, macbook va server bir xil ishlaydi.

Prometheus + Grafana ko'rib chiqildi va **rad etildi**: 700 MB+ RAM, uchta alohida
exporter va dashboard'larni qo'lda yig'ish kerak. Netdata bularning hammasini
qutidan chiqqan holda beradi.

---

## 1. `.env` ni to'ldirish

`.env.example` dagi "Monitoring" bo'limini `.env` ga ko'chiring. Minimal kerak
bo'ladiganlari:

```bash
MONITORING_HOSTNAME=logistika-server
NETDATA_PORT=19999
DOCKGE_PORT=5002
MONITORING_APP_NETWORK=logistika_bot_default
DOCKER_GID=999
```

Ikkita qiymatni serverda tekshiring:

```bash
# 1) Ilova tarmog'ining aniq nomi (odatda <papka nomi>_default)
docker network ls | grep default

# 2) docker.sock guruh raqami
stat -c '%g' /var/run/docker.sock
```

Chiqqan qiymatlarni `MONITORING_APP_NETWORK` va `DOCKER_GID` ga yozing.

> `MONITORING_APP_NETWORK` noto'g'ri bo'lsa `make mon-up` "network not found"
> xatosi bilan to'xtaydi — bu yaxshi, jimgina noto'g'ri ishlamaydi.

---

## 2. PostgreSQL uchun faqat-o'qish rol (tavsiya etiladi)

Standart holda Netdata `.env` dagi `DB_USER` bilan ulanadi. Ishlaydi, lekin
monitoring uchun to'liq huquqli foydalanuvchi kerak emas. Xavfsizroq variant:

```bash
docker compose exec db psql -U postgres -c \
  "CREATE USER netdata WITH PASSWORD 'monitoring_uchun_parol';"
docker compose exec db psql -U postgres -c \
  "GRANT pg_monitor TO netdata;"
```

So'ng `.env` ga:

```bash
NETDATA_PG_USER=netdata
NETDATA_PG_PASSWORD=monitoring_uchun_parol
```

`pg_monitor` — PostgreSQL'ning o'zida tayyor rol: statistika ko'radi, ma'lumot
o'qiy olmaydi va o'zgartira olmaydi.

---

## 3. Ishga tushirish

```bash
make mon-up
```

Bu ikki ishni qiladi:

1. `monitoring/render-config.py` — `monitoring/netdata/**` shablonlaridagi `${VAR}`
   larni `.env` qiymatlari bilan to'ldirib, `monitoring/.rendered/` ga yozadi.
   (Netdata konfiguratsiya fayllarida o'zgaruvchilarni o'zi kengaytirmaydi, shuning
   uchun bu qadam kerak. Natijada parollar git'ga tushmaydi.)
2. `docker compose -f docker-compose.monitoring.yml up -d`

Tekshirish:

```bash
make mon-ps
curl -s http://localhost:19999/api/v1/info | head -5
```

Konfiguratsiyani o'zgartirgandan keyin: **`make mon-restart`** (shunchaki
`docker restart` emas — render qadamini o'tkazib yuborardi).

---

## 4. Panelni ochish (SSH tunnel)

Ikkala panel ham serverda **faqat `127.0.0.1`** ga bog'langan — server IP'sidan
yoki internetdan ochilmaydi. Parol, domen, SSL kerak emas, chunki tashqi kirish
yo'lining o'zi yo'q.

Kompyuteringizda (serverda emas):

```bash
ssh -N -L 19999:localhost:19999 -L 5002:localhost:5002 foydalanuvchi@server-ip
```

Terminal ochiq turadi (bu normal). Brauzerda:

- **Netdata** → http://localhost:19999
- **Dockge** → http://localhost:5002

Buyruqni eslab qolish shart emas: `make mon-tunnel` uni chop etadi.

Qo'shimcha himoya qatlami (ixtiyoriy, bind allaqachon localhost):

```bash
sudo ufw deny 19999
sudo ufw deny 5002
```

---

## 5. Telegram alertlari

Muammo yuz berganda xabar keladi: konteyner o'chdi, disk to'ldi, RAM tugadi,
Postgres ulanishlari limitga yaqinlashdi, RabbitMQ navbati o'sib ketdi.

1. Alohida bot yarating ([@BotFather](https://t.me/BotFather)) — asosiy `BOT_TOKEN`
   ni ishlatish mumkin, lekin alohidasi tozaroq.
2. Botga `/start` yozing, chat ID'ni oling:
   ```bash
   curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | grep -o '"id":[0-9-]*' | head -1
   ```
3. `.env` ga:
   ```bash
   MONITORING_TG_TOKEN=123456:AAAA...
   MONITORING_TG_CHAT_ID=123456789
   ```
4. `make mon-restart`
5. Tekshirish:
   ```bash
   make mon-alert-test
   ```
   Telegram'ga bir nechta namunaviy xabar kelishi kerak.

Guruhga yuborish uchun: botni guruhga qo'shing, chat ID manfiy bo'ladi
(`-1001234567890`) — o'shani yozing.

### Qanday alertlar sozlangan

Netdata'ning o'zidagi tayyor alertlar (disk to'lishi, RAM, CPU, swap, tarmoq
xatolari) ustiga `monitoring/netdata/health.d/logistika.conf` da beshtasi qo'shilgan:

| Alert | Qachon ishlaydi |
|---|---|
| `logistika_containers_down` | Ishlab turgan konteynerlar soni `MONITORING_EXPECTED_CONTAINERS` dan kam |
| `logistika_containers_unhealthy` | Kamida bitta konteyner healthcheck'dan o'tmayapti |
| `logistika_endpoint_unreachable` | `web`, `web→db`, `support` yoki `osrm` so'rovlarga javob bermayapti |
| `logistika_queue_backlog` | RabbitMQ navbatida xabarlar to'planib qoldi |
| `logistika_pg_connections` | Postgres ulanishlari limitning 75% / 90% idan oshdi |

> **Restartdan keyin alertlar bir necha daqiqa `UNINITIALIZED` turadi** — bu normal.
> Har bir alert `lookup` oynasi (1-2 daqiqa) to'lgunicha hisoblanmaydi. `CLEAR`
> holatiga o'tgach ishlay boshlaydi. Tekshirish:
> ```bash
> curl -s 'http://localhost:19999/api/v1/alarms?all' | grep -c UNINITIALIZED
> ```

---

## 6. Nimaga e'tibor berish kerak

**Netdata panelida:**

| Bo'lim | Nima ko'rsatadi |
|---|---|
| System Overview | Umumiy CPU, RAM, disk, tarmoq |
| Containers & VMs | Har bir konteyner: `logistika_web_prod`, `aiogram_telegram_bot`, ... |
| PostgreSQL | Ulanishlar, tranzaksiyalar, cache hit-rate, sekin so'rovlar |
| Redis | Xotira, kalitlar, hit-rate |
| RabbitMQ | Navbat uzunligi, "unacked" xabarlar |
| HTTP Checks | 4 ta tekshiruv: `web` (`/health`), `web` → baza (`/health/db`), `support` (`/health`), `osrm` (haqiqiy marshrut) |
| Alerts | Faol ogohlantirishlar |

**Loyihaga xos ikki muhim ko'rsatkich:**

- **RabbitMQ → `queue_messages_count`** — dispatch navbatining uzunligi. O'sib
  borsa worker'lar ulgurmayapti: `make worker-scale n=3`.
- **HTTP Checks → `osrm_router`** — OSRM haqiqiy marshrut qaytaryaptimi. Bu
  yiqilsa narx hisoblash butunlay to'xtaydi (`/orders/estimate-price` → 503).

---

## 7. Resurs iste'moli

`monitoring/netdata/netdata.conf` da yengillashtirilgan:

- `update every = 2` — 1 soniya o'rniga (CPU ikki barobar kam)
- `[ml] enabled = no` — anomaliya detektori o'chirilgan
- tarix uchun disk 256 MB bilan cheklangan (≈ 3-4 kun)
- keraksiz plaginlar (`python.d`, `charts.d`, `perf`, `slabinfo`, `ebpf`) o'chirilgan

Tekshirish:

```bash
docker stats --no-stream logistika_netdata logistika_dockge
```

Kutilgan natija: Netdata ~100–150 MB, Dockge ~50 MB, CPU 1–3%.

Ko'proq tarix kerak bo'lsa `dbengine multihost disk space MB` ni oshiring
(1024 ≈ 2 hafta) va `make mon-restart` qiling.

---

## 8. Nosozliklar

**`network logistika_bot_default not found`**
Ilova stack'i ko'tarilmagan yoki tarmoq nomi boshqacha.
`docker network ls` → to'g'ri nomni `.env` dagi `MONITORING_APP_NETWORK` ga yozing.

**Konteynerlar grafikda ID bilan ko'rinadi (nomi emas)**
Netdata `docker.sock` ni o'qiy olmayapti. `stat -c '%g' /var/run/docker.sock`
natijasini `.env` dagi `DOCKER_GID` ga yozib, `make mon-restart`.

**PostgreSQL / Redis / RabbitMQ bo'limlari bo'sh**
```bash
make mon-collectors      # kollektor xatolari
```
Sabablari odatda: parol noto'g'ri, yoki xizmat konteynerda emas — host mashinada.
Ikkinchi holatda `.env` da manzilni almashtiring:
```bash
NETDATA_PG_HOST=host.docker.internal
NETDATA_REDIS_HOST=host.docker.internal
NETDATA_RABBITMQ_HOST=host.docker.internal
```
Host'dagi Postgres uchun qo'shimcha: `postgresql.conf` da
`listen_addresses = '*'` va `pg_hba.conf` ga docker tarmog'i uchun ruxsat
(`host all netdata 172.16.0.0/12 scram-sha-256`), so'ng `systemctl reload postgresql`.

**Telegram'ga xabar kelmayapti**
```bash
make mon-alert-test
```
Chiqishda `# SENT telegram notification` bo'lishi kerak. `not sent` bo'lsa —
token/chat ID noto'g'ri yoki botga hali `/start` yozilmagan.

**"Konteynerlar soni kam" alerti noto'g'ri ishlayapti**
`.env` dagi `MONITORING_EXPECTED_CONTAINERS` ni haqiqiy songa moslang:
`docker ps -q | wc -l`.

---

## 9. Konfiguratsiyani tahrirlashda ikkita tuzoq

Ikkalasi ham **xato bermaydi** — shunchaki jimgina ishlamay qo'yadi, shuning uchun
alohida eslatib o'tilyapti.

**1. `netdata.conf` va `health.d/*.conf` da qator oxirida izoh yozib bo'lmaydi.**
Netdata qiymatni qator oxirigacha o'qiydi:

```ini
cgroups = yes   # izoh    ← qiymat "yes   # izoh" bo'ladi, plagin O'CHADI
```

To'g'risi — izoh alohida qatorda:

```ini
# Docker konteynerlari resursi shu yerdan keladi
cgroups = yes
```

(`go.d/*.conf` — YAML, u yerda qator oxiridagi izoh muammosiz. `.env` uchun ham
shu qoida: qiymatdan keyin izoh yozmang.)

**2. Alertlarda `template:` ishlatiladi, `alarm:` emas.**
`alarm:` da `on:` grafikning aniq id'sini talab qiladi (`docker_local.containers_state`)
— u job nomiga bog'liq va o'zgarib ketishi mumkin. `template:` da esa `on:` —
kontekst (`docker.containers_state`), ya'ni barcha mos grafiklarga qo'llanadi.
Mavjud kontekstlarni ko'rish:

```bash
curl -s localhost:19999/api/v1/charts \
  | python3 -c "import sys,json;[print(v['context']) for v in json.load(sys.stdin)['charts'].values()]" \
  | sort -u
```

Alert haqiqatan ro'yxatdan o'tganini tekshirish:

```bash
curl -s 'http://localhost:19999/api/v1/alarms?all' | grep -c logistika_
```

---

## 10. Macbook (lokal) haqida

Netdata macbookda ham ishga tushadi, konteynerlar va kollektorlar to'g'ri ishlaydi,
lekin **host metrikalari Mac'niki emas, Docker Desktop virtual mashinasiniki**
bo'ladi (CPU/RAM/disk raqamlari Mac'nikiga to'g'ri kelmaydi). Bu kutilgan holat —
konfiguratsiya ataylab Ubuntu serverga moslangan. Lokalda asosan "ishga tushdimi,
kollektorlar ulandimi" ni tekshirish uchun foydali.

**Dockge macbookda ishlamaydi:** `/opt/stacks` Docker Desktop'ning "File Sharing"
ro'yxatida yo'q va konteyner ko'tarilmaydi. Lokalda faqat Netdata'ni ishga tushiring:

```bash
python3 monitoring/render-config.py
docker compose -f docker-compose.monitoring.yml up -d netdata
```

Yoki `.env` da `DOCKGE_STACKS_DIR` ni `/Users` ostidagi biror papkaga o'zgartiring.
Serverda (Ubuntu) bunday cheklov yo'q — `sudo mkdir -p /opt/stacks` yetadi.

---

## Buyruqlar ro'yxati

```
make mon-up           # ishga tushirish (konfiguratsiyani render qilib)
make mon-down         # to'xtatish (metrikalar tarixi saqlanadi)
make mon-restart      # konfiguratsiya o'zgargandan keyin
make mon-ps           # holat
make mon-logs         # Netdata loglari
make mon-collectors   # qaysi kollektor ulandi / ulanmadi
make mon-alert-test   # Telegram sozlamasini tekshirish
make mon-tunnel       # SSH tunnel buyrug'ini ko'rsatadi
```
