import { useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import './admin-global.css';
import { AdminLayout } from './AdminLayout';
import { ToastProvider } from './components/Toast';
import { AdminDashboard } from './pages/AdminDashboard';
import { AdminDrivers } from './pages/AdminDrivers';
import { AdminOrders } from './pages/AdminOrders';
import { AdminSettings } from './pages/AdminSettings';
import { AdminTickets } from './pages/AdminTickets';
import { AdminTruckTypes } from './pages/AdminTruckTypes';
import { AdminUsers } from './pages/AdminUsers';

export function AdminApp() {
  // Admin — desktop panel: index.css dagi #root 480px cheklovini ochish uchun belgi qo'yamiz.
  useEffect(() => {
    document.documentElement.setAttribute('data-admin', '');
    return () => document.documentElement.removeAttribute('data-admin');
  }, []);

  return (
    <ToastProvider>
      <Routes>
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminDashboard />} />
          <Route path="orders" element={<AdminOrders />} />
          <Route path="drivers" element={<AdminDrivers />} />
          <Route path="users" element={<AdminUsers />} />
          <Route path="truck-types" element={<AdminTruckTypes />} />
          <Route path="tickets" element={<AdminTickets />} />
          <Route path="settings" element={<AdminSettings />} />
        </Route>
        <Route path="*" element={<Navigate to="/admin" replace />} />
      </Routes>
    </ToastProvider>
  );
}
