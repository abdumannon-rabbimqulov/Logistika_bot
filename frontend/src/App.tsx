import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { GuestRoute } from "./components/GuestRoute";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { RootRedirect } from "./components/RootRedirect";
import { AdminLayout } from "./layouts/AdminLayout";
import { MobileAppLayout } from "./layouts/MobileAppLayout";
import { Login } from "./pages/Login";
import { ForgotPasswordPage } from "./pages/auth/ForgotPasswordPage";
import { Dashboard } from "./pages/Dashboard";
import { Orders } from "./pages/Orders";
import { Users } from "./pages/Users";
import { AICommands } from "./pages/AICommands";
import { LiveTracking } from "./pages/LiveTracking";
import { Profile } from "./pages/Profile";
import { SenderHome } from "./pages/SenderHome";
import { DriverHome } from "./pages/DriverHome";
import { DriverSetupProfile } from "./pages/DriverSetupProfile";
import { MobileProfile } from "./pages/mobile/MobileProfile";
import { TruckTypesAdmin } from "./pages/admin/TruckTypesAdmin";

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
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
                <MobileAppLayout role="driver" />
              </ProtectedRoute>
            }
          >
            <Route index element={<DriverHome />} />
            <Route path="profile" element={<MobileProfile />} />
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
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
