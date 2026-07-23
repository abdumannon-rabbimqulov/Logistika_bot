import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { initTelegramWebApp } from './telegram'
import { loadYandexMaps } from './utils/yandexMaps'

initTelegramWebApp()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)

// Xarita skriptini fon rejimida, bo'sh vaqtda oldindan yuklab qo'yamiz. Shunda
// foydalanuvchi buyurtma sahifasini ochganda xarita allaqachon tayyor bo'ladi va
// birinchi ochilishdagi kutish (skript yuklab olish) yo'qoladi. Dastlabki render'ga
// xalaqit bermasligi uchun requestIdleCallback ishlatiladi.
const preloadMap = () => void loadYandexMaps().catch(() => {})
if ('requestIdleCallback' in window) {
  requestIdleCallback(preloadMap, { timeout: 3000 })
} else {
  setTimeout(preloadMap, 1500)
}
