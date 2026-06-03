import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getPathForSession } from "../auth/redirect";
import type { UserRole } from "../types/auth";

interface ProtectedRouteProps {
  children: React.ReactNode;
  /** Ruxsat berilgan rollar. Bo'sh bo'lsa — faqat token tekshiriladi. */
  roles?: UserRole[];
  /** Haydovchi profil to'ldirish sahifasi uchun */
  allowNeedProfile?: boolean;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  roles,
  allowNeedProfile = false,
}) => {
  const { loading, isAuthenticated, session } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="layout-loading">
        <div className="spinner" />
        <p>Yuklanmoqda...</p>
      </div>
    );
  }

  if (!isAuthenticated || !session) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (session.status === "need_driver_profile" && !allowNeedProfile) {
    return <Navigate to="/driver/setup-profile" replace />;
  }

  if (roles && roles.length > 0 && !roles.includes(session.role)) {
    return <Navigate to={getPathForSession(session)} replace />;
  }

  return <>{children}</>;
};
