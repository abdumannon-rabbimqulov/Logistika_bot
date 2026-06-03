import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getPathForSession } from "../auth/redirect";

export const RootRedirect: React.FC = () => {
  const { loading, session, isAuthenticated } = useAuth();

  if (loading) {
    return (
      <div className="layout-loading">
        <div className="spinner" />
        <p>Yuklanmoqda...</p>
      </div>
    );
  }

  if (!isAuthenticated || !session) {
    return <Navigate to="/login" replace />;
  }

  return <Navigate to={getPathForSession(session)} replace />;
};
