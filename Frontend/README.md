# YUK — Telegram Mini App (sender)

Logistika platformasining sender (yuk beruvchi) uchun Telegram Mini App frontendi. React + Vite +
TypeScript, backend (`../order`, `../users`, `../driver`) bilan REST API orqali ishlaydi.

Dizayn manbai: `../design_handoff_yuk_asosiy_ekranlar/`.

## Ikki xil ishga tushirish — qaysi portni ochish kerak

Loyihada frontend uchun IKKITA alohida stack bor. Ishlab chiqish paytida faqat birinchisi
ishlatiladi:

| Port | Konteyner | Compose fayli | Nima beradi | Kod o'zgarganda |
|------|-----------|---------------|-------------|-----------------|
| **5173** | `yuk_frontend_dev` | `../docker-compose.yml` (ildizda) | Vite dev serveri | **HMR — darhol aks etadi** |
| 8080 | `yuk_frontend` | `./docker-compose.yml` (shu papkada) | nginx + statik `dist/` | qayta build kerak |

**Ishlab chiqishda http://localhost:5173 ni oching.** 8080-port image ichiga "qotirilgan"
`dist/` ni beradi — u yerda har bir o'zgarish uchun qayta build kerak bo'lishi kutilgan holat,
nosozlik emas. Ikkalasini birdan ishlatmang: ikki port ikki xil kodni ko'rsatadi.

### Docker bilan (tavsiya etiladi)

Repo ildizidan (`cd ..`):

```bash
docker compose up -d frontend      # http://localhost:5173 — HMR tayyor
docker compose logs -f frontend    # `[vite] (client) hmr update ...` shu yerda ko'rinadi
```

Manba kod `./Frontend:/app` orqali bind-mount qilingan, shuning uchun faylni saqlash bilanoq
brauzerda aks etadi — `--build` SHART EMAS.

Faqat `package.json` o'zgarganda (yangi paket qo'shilganda) qayta build kerak, va aynan shu
bayroq bilan — aks holda eski `node_modules` anonim volume'i saqlanib qoladi va Vite chalg'ituvchi
`Failed to resolve import` xatosini beradi:

```bash
docker compose up -d --build --renew-anon-volumes frontend
```

### Docker'siz (host'da)

```bash
npm install
cp .env.example .env   # VITE_API_BASE_URL ni backend manziliga moslang
npm run dev
```

### Brauzerda ochish

Ilova Telegram Mini App sifatida `window.Telegram.WebApp.initData` orqali login qiladi. Telegram
tashqarisida (masalan `http://localhost:5173`) ochilsa xato bermaydi — telefon+parol bilan kirish
formasi ko'rsatiladi (`src/auth/AuthProvider.tsx` → `status: 'local-login'` → `LocalLoginPage`).

Haqiqiy Telegram ichida sinash uchun HTTPS tunnel kerak (Telegram faqat HTTPS qabul qiladi):

```bash
npm run dev:tunnel   # VITE_TUNNEL=1 — HMR websocket'i wss://...:443 ga yo'naltiriladi
```

## Build

```bash
npm run build   # dist/ ga statik build
```

`dist/` papkasini HTTPS orqali joylashtiring va bot'dagi `WEBAPP_URL` (`.env`, repo ildizida)
o'sha manzilga ishora qilishi kerak — Telegram WebApp tugmasi faqat HTTPS bilan ishlaydi.
