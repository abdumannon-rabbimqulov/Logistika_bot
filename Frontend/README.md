# YUK — Telegram Mini App (sender)

Logistika platformasining sender (yuk beruvchi) uchun Telegram Mini App frontendi. React + Vite +
TypeScript, backend (`../order`, `../users`, `../driver`) bilan REST API orqali ishlaydi.

Dizayn manbai: `../design_handoff_yuk_asosiy_ekranlar/`.

## Ishga tushirish

Barcha buyruqlar **repo ildizidan** (`cd ..`) beriladi. `Makefile` shunchaki `docker compose`
qisqartmalari — istasangiz to'liq buyruqni qo'lda yozishingiz mumkin.

```bash
make fe          # ⇒ docker compose up -d frontend   → http://localhost:5173
make fe-logs     # `[vite] (client) hmr update ...` shu yerda ko'rinadi
make dev         # frontend + backend (web)
make             # barcha buyruqlar ro'yxati
```

`make fe` backendni **kutmaydi** (frontend'da `depends_on` yo'q) — bir necha soniyada tayyor.
Vite `/api` so'rovlarini `web:8000` ga proxy qiladi, shuning uchun backendni keyinroq
(`make dev`) ko'tarsangiz ham ishlaydi.

| Rejim | Buyruq | Port | Nima beradi | Kod o'zgarganda |
|-------|--------|------|-------------|-----------------|
| **dev** | `make fe` | **5173** | Vite dev serveri | **HMR — darhol aks etadi** |
| prod | `make prod-up` | — (oldida Caddy: 443) | nginx + statik `dist/` | qayta build kerak |

Ikkalasi ham bitta `frontend` xizmatining ikki rejimi (`docker-compose.yml` va uning ustidagi
`docker-compose.prod.yml`), shuning uchun ular bir vaqtda ishlamaydi — chalkashlik yo'q.
Image teglari alohida (`yuk_frontend_dev` / `yuk_frontend`), ya'ni `make prod-up` dev image'ni
buzmaydi va rejimlar orasida bemalol o'tish mumkin.

### Kundalik ish

`src/` va `public/` host'dan bind-mount qilingan, shuning uchun **kod o'zgarishi uchun hech
narsa qilish shart emas** — saqlaysiz, HMR brauzerda aks ettiradi.

Qayta build faqat **image ichidagi** fayllar o'zgarganda kerak — ya'ni `package.json`,
`vite.config.ts`, `index.html`, `tsconfig*.json`:

```bash
make fe-rebuild         # ~10 soniya (npm ci qatlami va BuildKit npm keshi saqlanadi)
make fe-add pkg=zod     # host'da npm install + fe-rebuild — bitta buyruqda
```

> **Nima uchun butun papka mount qilinmaydi.** Ilgari `./Frontend:/app` to'liq mount qilinib,
> `node_modules` ustiga alohida volume qo'yilardi. Docker Desktop (macOS) bind-mount ichidagi
> volume'ni ishonchli "yopmaydi" — konteyner baribir host'dagi `Frontend/node_modules` ni
> ko'rardi va u yerga linux/musl nativ binarlarni (rolldown, oxlint) yozib qo'yardi. Natijada
> host'da `npm run build` `Cannot find native binding` bilan yiqilar, fayllar esa root
> egaligida qolardi. Endi konteyner `node_modules` ni o'z qatlamida saqlaydi va host'dagi
> `Frontend/node_modules` mutlaqo mustaqil.

### Docker'siz (host'da)

```bash
make fe-install        # ⇒ cd Frontend && npm ci  (lock fayl bo'yicha aniq versiyalar)
cp .env.example .env   # VITE_API_BASE_URL ni backend manziliga moslang
npm run dev
```

Node **22+** kerak (`vite@8` / `oxlint` `engines: ^20.19.0 || >=22.12.0` talab qiladi).
`make fe-build` va `make fe-lint` ham host'dagi `node_modules` bilan ishlaydi.

### Brauzerda ochish

Ilova Telegram Mini App sifatida `window.Telegram.WebApp.initData` orqali login qiladi. Telegram
tashqarisida (masalan `http://localhost:5173`) ochilsa xato bermaydi — telefon+parol bilan kirish
formasi ko'rsatiladi (`src/auth/AuthProvider.tsx` → `status: 'local-login'` → `LocalLoginPage`).

Haqiqiy Telegram ichida sinash uchun HTTPS tunnel kerak (Telegram faqat HTTPS qabul qiladi):

```bash
npm run dev:tunnel   # VITE_TUNNEL=1 — HMR websocket'i wss://...:443 ga yo'naltiriladi
```

## Build va deploy

```bash
make fe-build          # konteyner ichida: tsc -b && vite build → dist/
npm run build          # yoki host'da
```

Server uchun repo ildizidan:

```bash
make deploy            # serverda: tekshiruvlar + build + up + healthcheck
make prod-local        # kompyuterda: aynan o'sha stack, DOMAIN=localhost
```

To'liq qo'llanma: [docs/DEPLOY.md](../docs/DEPLOY.md).

Bu `frontend` xizmatini nginx rejimida quradi (`Frontend/Dockerfile`). Konteyner
tashqariga port ochmaydi — oldida Caddy turadi va HTTPS'ni (Let's Encrypt, avtomatik)
u ta'minlaydi. nginx esa `/api`, `/support`, `/static` va `/osrm` ni compose
tarmog'idagi tegishli xizmatlarga uzatadi.

`VITE_API_BASE_URL` build vaqtida bundle'ga "quyiladi" (Vite env'lari runtime'da
o'qilmaydi) — backend manzili o'zgarsa `--build` bilan qayta quring. Qiymatlar repo
ildizidagi `.env` dan olinadi (namuna `.env.example` da).

Frontend HTTPS orqali ochilishi va bot'dagi `WEBAPP_URL` (`.env`, repo ildizida) o'sha manzilga
ishora qilishi kerak — Telegram WebApp tugmasi faqat HTTPS bilan ishlaydi.
