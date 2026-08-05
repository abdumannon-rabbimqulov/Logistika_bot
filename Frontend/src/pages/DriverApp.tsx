import { useState } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { getMyDriverCabinetOrNull } from '../api/drivers';
import type { DriverCabinet } from '../types/api';
import { CabinetContext } from './DriverCabinetContext';
import { DriverActiveOrderPage } from './DriverActiveOrderPage';
import { DriverEarningsPage } from './DriverEarningsPage';
import { DriverHomePage } from './DriverHomePage';
import { DriverOrdersPage } from './DriverOrdersPage';
import { DriverProfilePage } from './DriverProfilePage';
import { MessagesPage } from './MessagesPage';
import { TicketPage } from './TicketPage';

interface Props {
  initialCabinet: DriverCabinet;
}

export function DriverApp({ initialCabinet }: Props) {
  const [cabinet, setCabinet] = useState<DriverCabinet>(initialCabinet);

  async function reloadCabinet() {
    const fresh = await getMyDriverCabinetOrNull();
    if (fresh) setCabinet(fresh);
  }

  return (
    <CabinetContext.Provider value={{ cabinet, setCabinet, reloadCabinet }}>
      <Routes>
        <Route path="/" element={<DriverHomePage />} />
        <Route path="/active/:orderId" element={<DriverActiveOrderPage />} />
        <Route path="/orders" element={<DriverOrdersPage />} />
        <Route path="/earnings" element={<DriverEarningsPage />} />
        {/* Murojaatlar haydovchi uchun ham ochiq — support har qanday autentifikatsiyalangan
            foydalanuvchini qabul qiladi (get_principal), rol farqi yo'q. */}
        <Route path="/messages" element={<MessagesPage />} />
        <Route path="/messages/:ticketId" element={<TicketPage />} />
        <Route path="/profile" element={<DriverProfilePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </CabinetContext.Provider>
  );
}
