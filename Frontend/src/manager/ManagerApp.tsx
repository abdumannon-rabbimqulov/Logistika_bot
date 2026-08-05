import { useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import '../admin/admin-global.css';
import { ToastProvider } from '../admin/components/Toast';
// Murojaatlar ekrani xodim (admin/manager) uchun bir xil — support tomonda ham ruxsat
// `require_staff` bilan beriladi, shuning uchun alohida nusxa yozilmaydi.
import { AdminTickets } from '../admin/pages/AdminTickets';
import { ManagerLayout } from './ManagerLayout';
import { ManagerOrderDetailPage } from './pages/ManagerOrderDetailPage';
import { ManagerOrders } from './pages/ManagerOrders';

// Menejer paneli — admin panel bilan bir xil desktop qobiq va komponentlardan
// foydalanadi (DataTable, Modal, Toast, shared.module.css), lekin BOSHQA endpointlar
// (`/manager/...`) va narxsiz ma'lumot ustida ishlaydi.

export function ManagerApp() {
  // Admin panel bilan bir xil belgi — index.css dagi #root 480px cheklovini ochadi
  // (admin-global.css aynan `html[data-admin]` ga bog'langan, shuning uchun shu nom).
  useEffect(() => {
    document.documentElement.setAttribute('data-admin', '');
    return () => document.documentElement.removeAttribute('data-admin');
  }, []);

  return (
    <ToastProvider>
      <Routes>
        <Route path="/manager" element={<ManagerLayout />}>
          <Route index element={<ManagerOrders />} />
          <Route path="orders" element={<ManagerOrders />} />
          <Route path="orders/:orderId" element={<ManagerOrderDetailPage />} />
          <Route path="tickets" element={<AdminTickets />} />
        </Route>
        <Route path="*" element={<Navigate to="/manager" replace />} />
      </Routes>
    </ToastProvider>
  );
}
