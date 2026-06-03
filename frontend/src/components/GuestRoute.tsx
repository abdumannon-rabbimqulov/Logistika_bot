import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getPathForSession } from "../auth/redirect";

interface GuestRouteProps {
  children: React.ReactNode;
}

/** Login sahifasi — allaqachon kirgan bo'lsa roliga qarab yo'naltiradi. */
export const GuestRoute: React.FC<GuestRouteProps> = ({ children }) => {
  const { loading, isAuthenticated, session } = useAuth();

  if (loading) {
    return (
      <div className="layout-loading">
        <div className="spinner" />
        <p>Yuklanmoqda...</p>
      </div>
    );
  }

  if (isAuthenticated && session) {
    return <Navigate to={getPathForSession(session)} replace />;
  }

  return <>{children}</>;
};
