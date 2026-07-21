import { Navigate, Route, Routes } from 'react-router-dom';
import styles from './App.module.css';
import { AuthProvider, useAuth } from './auth/AuthProvider';
import { DriverGate } from './pages/DriverGate';
import { HomePage } from './pages/HomePage';
import { LocalLoginPage } from './pages/LocalLoginPage';
import { MessagesPage } from './pages/MessagesPage';
import { OrderPage } from './pages/OrderPage';
import { OrderTrackingPage } from './pages/OrderTrackingPage';
import { OrdersListPage } from './pages/OrdersListPage';
import { ProfilePage } from './pages/ProfilePage';
import { RegisterPage } from './pages/RegisterPage';

function SenderApp() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/order/new" element={<OrderPage />} />
      <Route path="/orders" element={<OrdersListPage />} />
      <Route path="/orders/:orderId" element={<OrderTrackingPage />} />
      <Route path="/messages" element={<MessagesPage />} />
      <Route path="/profile" element={<ProfilePage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function AuthGate() {
  const { status, errorMessage, retry } = useAuth();

  switch (status) {
    case 'loading':
      return (
        <div className={styles.centerScreen}>
          <div className={styles.spinner} />
        </div>
      );

    case 'error':
      return (
        <div className={styles.centerScreen}>
          <div className={styles.wordmark}>YUK</div>
          <div className={styles.message}>{errorMessage ?? "Kirishda xato yuz berdi"}</div>
          <button className={styles.retryBtn} onClick={retry}>
            Qayta urinish
          </button>
        </div>
      );

    case 'local-login':
      return <LocalLoginPage />;

    case 'guest':
      return <RegisterPage />;

    case 'sender':
      return <SenderApp />;

    case 'driver':
      return <DriverGate />;

    case 'unsupported':
      return (
        <div className={styles.centerScreen}>
          <div className={styles.wordmark}>YUK</div>
          <div className={styles.message}>Bu ilova sender/haydovchi uchun. Sizning rolingiz uchun mo'ljallanmagan.</div>
        </div>
      );
  }
}

export default function App() {
  return (
    <AuthProvider>
      <AuthGate />
    </AuthProvider>
  );
}
