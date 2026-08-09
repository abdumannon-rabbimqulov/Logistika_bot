import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite dev serveri backend qayerda ekanini shu manzil orqali biladi. Odatda backend
// docker-compose orqali host'ning 8000-portida ochilgan. Kerak bo'lsa boshqacha qilib
// o'zgartirish mumkin: `VITE_DEV_API_TARGET=http://localhost:8003 npm run dev`.
const API_TARGET = process.env.VITE_DEV_API_TARGET || 'http://localhost:8000'

// Support — alohida mikroservis (o'z konteyneri, o'z bazasi). Docker tarmog'ida
// "support" nomi bilan 8000-portda, host'dan esa 8010-portda ochiq (SUPPORT_SERVICE_PORT).
const SUPPORT_TARGET = process.env.VITE_DEV_SUPPORT_TARGET || 'http://localhost:8010'

// OSRM — marshrut hisoblash. Buyurtma sahifasidagi Leaflet xaritasi (Leaflet Routing
// Machine) OSRM'ni BRAUZERDAN chaqiradi, shuning uchun unga nisbiy `/osrm` yo'li
// kerak. Docker tarmog'ida "osrm" nomi bilan 5000-portda, host'dan esa 5001-portda
// ochiq (docker-compose.yml da AirPlay bilan urishmasligi uchun 5001 qilingan).
const OSRM_TARGET = process.env.VITE_DEV_OSRM_TARGET || 'http://localhost:5001'

// ngrok orqali ishlatishda `VITE_TUNNEL=1 npm run dev` deb yoqiladi. Faqat shu holatda
// HMR websocket'i 443-portga (ngrok HTTPS) yo'naltiriladi. Oddiy local `npm run dev` da
// buni YOQMASLIK kerak — aks holda brauzer wss://localhost:443 ga urinib, HMR buziladi.
const TUNNEL = process.env.VITE_TUNNEL === '1'

// Docker konteynerida (bind-mount) fayl o'zgarishlari inotify orqali yetib kelmaydi —
// ayniqsa macOS/Windows host'ida. Shu sababli `CHOKIDAR_USEPOLLING=true` bo'lganda
// kuzatuvchi polling rejimiga o'tadi (docker-compose.yml `frontend` xizmati shu
// o'zgaruvchini beradi). Lokal `npm run dev` da esa polling YOQILMAYDI — u ortiqcha
// CPU sarflaydi va nativ hodisalar allaqachon ishlaydi.
const USE_POLLING =
  process.env.CHOKIDAR_USEPOLLING === 'true' || process.env.WATCHPACK_POLLING === 'true'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // 0.0.0.0 da tinglaydi — ngrok (yoki boshqa qurilma) tunnel qila olishi uchun.
    host: true,
    // ngrok tasodifiy host beradi (masalan xxxx.ngrok-free.app). Vite begona host'li
    // so'rovlarni default holda bloklaydi — `true` bilan tunnel host'iga ruxsat beriladi.
    // Bu faqat dev server (ishlab chiqarishga chiqmaydi), shuning uchun xavfsiz.
    allowedHosts: true,
    proxy: {
      // Frontend API'ni `/api` (nisbiy) orqali chaqiradi (Frontend/.env: VITE_API_BASE_URL=/api),
      // shunda brauzer uchun frontend va API bitta origin'da bo'ladi — CORS ham, ngrok ham
      // muammosiz. Bu yerda `/api` backendga uzatiladi (yo'l o'zgartirilmaydi: backend ham
      // `/api` prefiksi ostida ishlaydi — config API_PUBLIC_PREFIX).
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
        // WebSocket'lar ham shu prefiks ostida: haydovchining jonli GPS oqimi
        // (`/api/drivers/ws/location`) va admin xaritasi (`/api/system/drivers/locations/stream`).
        // `ws: true` bo'lmasa upgrade so'rovi oddiy HTTP sifatida uzatilib, ulanish uzilardi.
        ws: true,
      },
      // Support mikroservisi — yo'llari `/api` ostida EMAS, o'zining `/support` prefiksida
      // (support_service/router.py). Shu proxy bo'lmasa SPA unga umuman yeta olmaydi:
      // brauzer `/support/tickets` ni Vite'dan so'rab, SPA index.html olardi.
      // WebSocket yo'q — `ws: true` kerak emas.
      '/support': {
        target: SUPPORT_TARGET,
        changeOrigin: true,
      },
      // Backend yuklangan fayllarni `/static/uploads/...` ostida beradi (masalan admin
      // panelda yuklangan transport turi rasmi). Bu proxy bo'lmasa dev serverda rasm
      // o'rniga SPA index.html qaytardi.
      '/static': {
        target: API_TARGET,
        changeOrigin: true,
      },
      // Leaflet Routing Machine `/osrm/route/v1/driving/<koordinatalar>` ni so'raydi.
      // OSRM esa yo'lni prefiksiz kutadi (`/route/v1/driving/...`), shuning uchun
      // `/osrm` bo'lagi olib tashlanadi. Prod'da xuddi shu ish nginx'da qilinadi
      // (Frontend/nginx.conf) — ikkala muhitda frontend uchun yo'l bir xil.
      '/osrm': {
        target: OSRM_TARGET,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/osrm/, ''),
      },
    },
    // Docker'da fayl hodisalari uchun polling (yuqoridagi izohga qarang).
    watch: USE_POLLING ? { usePolling: true, interval: 300 } : undefined,
    // ngrok tunnelida HMR 443-port (wss) orqali ulanadi; oddiy local dev'da default qoladi.
    hmr: TUNNEL ? { protocol: 'wss', clientPort: 443 } : undefined,
  },
})
