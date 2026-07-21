# Handoff: Yuk (Logistika) Mobil Ilova — Asosiy Ekranlar

## Overview
Yuk tashish (freight/logistika) mobil ilovasi uchun 2 ta ekran: (1) buyurtma chaqirish ekrani — xarita + manzil + transport turi tanlash + narx, (2) ilova bosh sahifasi (home) — asosiy CTA, faol buyurtma, tezkor transport tanlash, saqlangan manzillar, oxirgi buyurtmalar, pastki navigatsiya.

## About the Design Files
Bu papkadagi HTML fayllar **dizayn referenslari** — ko'rinish va xatti-harakatni ko'rsatuvchi prototiplar, productionga to'g'ridan-to'g'ri qo'yiladigan kod emas. Vazifa: shu HTML dizaynlarni loyihaning haqiqiy muhitida (React Native, Flutter, native iOS/Android, yoki Telegram Mini App uchun React/Vue) qayta yaratish — mavjud kod bazasining o'rnatilgan patternlari va kutubxonalaridan foydalanib. Agar loyihada hali frontend muhiti yo'q bo'lsa (bu holatda — backend faqat Telegram bot + FastAPI, Mini App hali qurilmagan), eng mos frameworkni tanlab shu yerdan boshlash kerak.

## Fidelity
**High-fidelity (hifi)** — aniq ranglar (hex), tipografika, spacing va layout bilan pixel-perfect maketlar. Dasturchi UIni shu qiymatlar bilan aniq takrorlashi kerak.

## Screens / Views

### 1. Buyurtma chaqirish ekrani (`order-screen.dc.html`)
**Purpose:** Foydalanuvchi jo'natish/qabul qilish manzillarini ko'radi, transport turini tanlaydi, narxni ko'radi va buyurtma beradi.

**Layout:** iPhone frame ichida (393×852 dizayn kanvasi), to'liq ekran, absolute-positioned qatlamlar:
- Fon: to'liq ekranli sxematik xarita (statik, dekorativ — parklar, yo'llar, marshrut chizig'i, pin belgilar)
- Top bar: `top:64px`, ikkita 42px doira icon-tugma (orqaga, filtr) — `left:16px`/`right:16px`, space-between
- ETA badge marshrut ustida: pill shakl, soat ikonkasi + "17:12 da yetib keladi"
- Pickup nuqta: pulslovchi doira (jonli GPS effekti), destination: qora tomchi-pin
- Pastki sheet (`position:absolute; bottom:0`): oq fon, yuqori burchaklar radius 20px, yumshoq soya
  - Drag handle (36×4px, kulrang, pill, markazlashgan)
  - Manzil qatori 1: joriy manzil (avtomatik aniqlanadi) + "Qidirish" pill tugma (manzilni qidirib o'zgartirish uchun)
  - Manzil qatori 2: "Qayerga" manzili + "+" tugma
  - Transport-turi tab qatori (Hammasi / Sovutqich / Tentli / Bortli) — tanlangani pastki chiziq bilan
  - 4 ta transport karta gorizontal qatorda (Damas, Tentli, Sovutqich, Bortli): ikonka + vaqt + nom + narx; tanlangan karta (Tentli) — accent border + tint fon
  - CTA qator: chap/o'ng ikonka-tugma (to'lov usuli, sozlamalar) + markazda katta "Buyurtma berish" tugmasi (pill, accent rang)

**Components:**
- Manzil qatorlari: 20px doira icon/border, 2 qatorli matn (label kichik kulrang, qiymat qalin)
- Transport kartalar: 78×~100px, radius 14px, ikon 24px SVG chiziq (stroke, emoji YO'Q)
- Asosiy CTA tugma: to'liq kenglik, radius pill, accent fon, oq matn, 16px font, qalin

### 2. Bosh sahifa (`Yuk - Bosh Sahifa.dc.html`)
**Purpose:** Ilova ochilganda birinchi ko'rinadigan ekran — yangi buyurtma boshlash, faol buyurtmani kuzatish, tezkor qayta buyurtma.

**Layout:** Scroll bo'ladigan kontent (`bottom:78px` gacha) + fixed pastki navigatsiya (78px balandlik).
Yuqoridan pastga tartib:
1. **Top bar** (`padding:60px 20px 8px`): chapda "YUK" wordmark (Space Grotesk, 700, 20px), o'ngda bildirishnoma (qo'ng'iroq ikon + accent nuqta agar yangi bo'lsa) va profil ikon doiralari (40×40px, fon `#F4F5F7`)
2. **Asosiy CTA** (`padding:14px 20px 0`): oq karta, border `1.5px solid #EAECF0`, radius 20px, soya `0 2px 10px rgba(15,19,25,.06)`. Ichida: 42×42px accent-tint icon quti (pin ikonkasi), sarlavha "Qayerga yuk jo'natasiz?" (Space Grotesk 600/17px), yordamchi matn (Inter 13px, `#8A93A2`), o'ngda oq strelka. Bu ekrandagi ENG KO'ZGA TASHLANADIGAN element.
3. **Faol buyurtma kartasi** (agar mavjud bo'lsa): to'q fon `#0F1319`, oq matn, radius 20px. Status "YO'LDA" (accent rang, uppercase, 12px) + ETA raqami (Space Grotesk 700, 22px, "daq" kichik va xira). Pastda: haydovchi/mashina ikon quti, ism+mashina+tur, yo'nalish, va "Kuzatish" accent tugma.
4. **Tezkor transport tanlash**: sarlavha + gorizontal scroll qator, har biri 56×56px radius-16 icon quti (tanlangani accent-tint fon) + nom pastda.
5. **Saqlangan manzillar**: "Uy" va "Ish", 36×36px icon quti + ikki qatorli matn (nom qalin, manzil kulrang kichik), pastki chiziq bilan ajratilgan qatorlar.
6. **Oxirgi buyurtmalar**: karta ro'yxati (border 1px `#EAECF0`, radius 16px), chapda yo'nalish+sana+tur, o'ngda "Takrorlash" tugma (fon `#F4F5F7`).
7. **Banner** (ixtiyoriy, bitta): sokin fon `#F4F5F7`, radius 16px, info ikon + qisqa matn xavfsizlik haqida.
8. **Pastki navigatsiya** (fixed): 4 bo'lim — Bosh sahifa (faol, accent rang), Buyurtmalar, Xabarlar, Profil (barchasi kulrang `#8A93A2`), har biri ikon+label, flex:1 teng bo'linish.

## Interactions & Behavior
Bu statik dizayn ekranlari — hozircha klik/navigatsiya ishlamaydi (foydalanuvchi talabiga ko'ra). Implementatsiyada kutilayotgan xatti-harakatlar:
- Asosiy CTA bosilganda → manzil kiritish/qidiruv oqimiga o'tish
- "Qidirish" pill → manzil qidiruv modaliga ochish
- Transport karta/tanlov bosilganda → o'sha tur bilan buyurtma jarayoni boshlanadi, tanlangan holat vizual highlight bilan
- "Kuzatish" → faol buyurtma kuzatuv ekraniga o'tish (live GPS)
- "Takrorlash" → oldingi buyurtma manzillari bilan yangi buyurtma oqimi
- Pastki navigatsiya → mos bo'limga almashtirish, faol ikonka/label accent rangga o'tadi
- Pulslovchi GPS nuqta: `ds-pulse-dot` keyframe, 1.6s, ease-out, cheksiz takror (loop)

## State Management
- Faol buyurtma mavjud/yo'qligiga qarab "Faol buyurtma kartasi" ko'rsatiladi/yashiriladi
- Tanlangan transport turi (state) — tanlov o'zgarsa narx/vaqt yangilanadi
- Manzil inputlari (joriy manzil avtomatik GPSdan, destination — foydalanuvchi kiritadi/tanlaydi)
- Bildirishnoma nuqtasi — o'qilmagan xabar bor/yo'qligiga bog'liq
- Pastki navigatsiyada faol tab

## Design Tokens

**Ranglar:**
- Fon (asosiy): `#FFFFFF`
- Fon (sovuq kulrang, ikkinchi daraja): `#F4F5F7`
- Matn (asosiy, grafit-siyoh): `#0F1319`
- Matn (yordamchi): `#8A93A2`
- Chegara: `#EAECF0`
- Accent (burnt orange, faqat CTA/urg'u): `#EA5A15`
- Accent pressed: `#CE4C0C`
- Accent tint: `#FDEDE2`
- To'q karta fon (faol buyurtma): `#0F1319`

**Tipografika:**
- Sarlavha/raqam/ETA/narx: **Space Grotesk** (500/600/700 og'irlik)
- Body/yordamchi matn: **Inter** (400–700)
- Shkala: wordmark 20px/700, CTA sarlavha 17px/600, body 14px/500-600, yordamchi 12-13px/400, ETA raqam 22px/700

**Spacing/Radius:**
- Ekran padding: 20px gorizontal
- Karta radius: 16-20px (asosiy kartalar), 14px (transport kartalar), 10-12px (kichik icon quti)
- Icon quti: 36-56px turli joyларда (36px ro'yxat, 42px CTA icon, 56px transport tanlash)
- Pastki navigatsiya balandligi: 78px

**Soya:** faqat suzuvchi elementlarda (asosiy CTA karta) — `0 2px 10px rgba(15,19,25,.06)`. Boshqa kartalar flat border, soyasiz.

## Assets
Ikonkalar — barchasi custom inline SVG, chiziq (stroke) uslubida, `stroke-width: 1.6–1.9px`, emoji YO'Q. Xarita — statik dekorativ shakllar (real xarita integratsiyasi emas, placeholder).

## Files
- `order-screen.dc.html` — buyurtma chaqirish ekrani (asli: "Yuk Chaqirish - Asosiy Ekran.dc.html")
- `Yuk - Bosh Sahifa.dc.html` — bosh sahifa ekrani

Ikkala fayl ham brauzerda to'g'ridan-to'g'ri ochiladi (standalone HTML, tashqi bog'liqlik yo'q Google Fonts CDN'dan tashqari).
