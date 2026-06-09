import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { GuestRoute } from "./components/GuestRoute";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { RootRedirect } from "./components/RootRedirect";
import { AdminLayout } from "./layouts/AdminLayout";
import { MobileAppLayout } from "./layouts/MobileAppLayout";
import { DriverAppLayout } from "./layouts/DriverAppLayout";
import { LocationProvider } from "./context/LocationContext";
import { Login } from "./pages/Login";
import { ForgotPasswordPage } from "./pages/auth/ForgotPasswordPage";
import { Dashboard } from "./pages/Dashboard";
import { Orders } from "./pages/Orders";
import { Users } from "./pages/Users";
import { AICommands } from "./pages/AICommands";
import { LiveTracking } from "./pages/LiveTracking";
import { Profile } from "./pages/Profile";
import { SenderHome } from "./pages/SenderHome";
import { DriverHome } from "./pages/driver/DriverHome";
import { DriverOrdersPage } from "./pages/driver/DriverOrdersPage";
import { DriverSetupProfile } from "./pages/DriverSetupProfile";
import { DriverProfilePage } from "./pages/driver/DriverProfilePage";
import { DriverTripsPage } from "./pages/driver/DriverTripsPage";
import { DriverOrderDetailPage } from "./pages/driver/DriverOrderDetailPage";
import { AnnouncementsPage } from "./pages/driver/AnnouncementsPage";
import { AnnouncementOffersPage } from "./pages/driver/AnnouncementOffersPage";
import { MobileProfile } from "./pages/mobile/MobileProfile";
import { TruckTypesAdmin } from "./pages/admin/TruckTypesAdmin";
import { AIAssistantPage } from "./pages/sender/AIAssistantPage";
import { ChatsPage } from "./pages/sender/ChatsPage";
import { ChatDetailPage } from "./pages/sender/ChatDetailPage";
import { OrderCreatePage } from "./pages/sender/OrderCreatePage";
import { OrderListPage } from "./pages/sender/OrderListPage";
import { OrderDetailPage } from "./pages/sender/OrderDetailPage";

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <LocationProvider>
          <Routes>
            <Route
              path="/login"
              element={
                <GuestRoute>
                  <Login />
                </GuestRoute>
              }
            />
            <Route
              path="/forgot-password"
              element={
                <GuestRoute>
                  <ForgotPasswordPage />
                </GuestRoute>
              }
            />

            <Route
              path="/sender"
              element={
                <ProtectedRoute roles={["sender"]}>
                  <MobileAppLayout role="sender" />
                </ProtectedRoute>
              }
            >
              <Route index element={<SenderHome />} />
              <Route path="orders" element={<OrderListPage />} />
              <Route path="orders/create" element={<OrderCreatePage />} />
              <Route path="orders/:orderId" element={<OrderDetailPage />} />
              <Route path="ai" element={<AIAssistantPage />} />
              <Route path="chats" element={<ChatsPage />} />
              <Route path="chats/:chatId" element={<ChatDetailPage />} />
              <Route path="profile" element={<MobileProfile />} />
            </Route>

            <Route
              path="/driver/setup-profile"
              element={
                <ProtectedRoute roles={["driver"]} allowNeedProfile>
                  <DriverSetupProfile />
                </ProtectedRoute>
              }
            />

            <Route
              path="/driver"
              element={
                <ProtectedRoute roles={["driver"]}>
                  <DriverAppLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<DriverHome />} />
              <Route path="orders" element={<DriverOrdersPage />} />
              <Route path="orders/:orderId" element={<DriverOrderDetailPage />} />
              <Route path="trips" element={<DriverTripsPage />} />
              <Route path="profile" element={<DriverProfilePage />} />
              <Route path="announcements" element={<AnnouncementsPage />} />
              <Route path="announcements/:id" element={<AnnouncementOffersPage />} />
              <Route path="ai" element={<AIAssistantPage />} />
              <Route path="chats" element={<ChatsPage />} />
              <Route path="chats/:chatId" element={<ChatDetailPage />} />
            </Route>

            <Route
              element={
                <ProtectedRoute roles={["admin"]}>
                  <AdminLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/orders" element={<Orders />} />
              <Route path="/users" element={<Users />} />
              <Route path="/ai-commands" element={<AICommands />} />
              <Route path="/live-tracking" element={<LiveTracking />} />
              <Route path="/truck-types" element={<TruckTypesAdmin />} />
              <Route path="/profile" element={<Profile />} />
            </Route>

            <Route path="/" element={<RootRedirect />} />
            <Route path="*" element={<RootRedirect />} />
          </Routes>
        </LocationProvider>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
