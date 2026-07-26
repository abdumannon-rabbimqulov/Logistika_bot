import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite dev serveri backend qayerda ekanini shu manzil orqali biladi. Odatda backend
// docker-compose orqali host'ning 8000-portida ochilgan. Kerak bo'lsa boshqacha qilib
// o'zgartirish mumkin: `VITE_DEV_API_TARGET=http://localhost:8003 npm run dev`.
const API_TARGET = process.env.VITE_DEV_API_TARGET || 'http://localhost:8000'

// ngrok orqali ishlatishda `VITE_TUNNEL=1 npm run dev` deb yoqiladi. Faqat shu holatda
// HMR websocket'i 443-portga (ngrok HTTPS) yo'naltiriladi. Oddiy local `npm run dev` da
// buni YOQMASLIK kerak — aks holda brauzer wss://localhost:443 ga urinib, HMR buziladi.
const TUNNEL = process.env.VITE_TUNNEL === '1'

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
      // Backend yuklangan fayllarni `/static/uploads/...` ostida beradi (masalan admin
      // panelda yuklangan transport turi rasmi). Bu proxy bo'lmasa dev serverda rasm
      // o'rniga SPA index.html qaytardi.
      '/static': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
    // ngrok tunnelida HMR 443-port (wss) orqali ulanadi; oddiy local dev'da default qoladi.
    hmr: TUNNEL ? { protocol: 'wss', clientPort: 443 } : undefined,
  },
})
