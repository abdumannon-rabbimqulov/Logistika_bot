# YUK — Telegram Mini App (sender)

Logistika platformasining sender (yuk beruvchi) uchun Telegram Mini App frontendi. React + Vite +
TypeScript, backend (`../order`, `../users`, `../driver`) bilan REST API orqali ishlaydi.

Dizayn manbai: `../design_handoff_yuk_asosiy_ekranlar/`.

## Ishga tushirish

```bash
npm install
cp .env.example .env   # VITE_API_BASE_URL ni backend manziliga moslang
npm run dev
```

Bu ilova faqat Telegram Mini App sifatida to'liq ishlaydi (`window.Telegram.WebApp.initData`
orqali login qiladi) — oddiy brauzerda ochilsa aniq xato xabari ko'rsatiladi.

## Build

```bash
npm run build   # dist/ ga statik build
```

`dist/` papkasini HTTPS orqali joylashtiring va bot'dagi `WEBAPP_URL` (`.env`, repo ildizida)
o'sha manzilga ishora qilishi kerak — Telegram WebApp tugmasi faqat HTTPS bilan ishlaydi.
