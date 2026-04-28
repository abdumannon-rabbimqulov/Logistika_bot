import React, { createContext, useContext, useEffect, useState } from 'react';
import api from './api';

const AuthContext = createContext(null);

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [needsRoleSelection, setNeedsRoleSelection] = useState(false);

  useEffect(() => {
    const initAuth = async () => {
      try {
        const tg = window.Telegram?.WebApp;
        
        if (tg) {
          tg.ready();
          // To see the Mini App full height
          tg.expand();
        }

        // 1. Check if we have initData (running in Telegram)
        const initData = tg?.initData;
        let token = localStorage.getItem('access_token');

        if (initData) {
          const res = await api.post('/auth/telegram/webapp-login', { init_data: initData });
          token = res.data.access_token;
          localStorage.setItem('access_token', token);
          if (res.data.refresh_token) {
            localStorage.setItem('refresh_token', res.data.refresh_token);
          }
        } else if (!token && window.location.hostname === 'localhost') {
           // Dev Mode Bypass: If on localhost and no token/initData, use a mock flow
           console.warn("Dev Mode: No Telegram initData found. Please login via bot or provide a token.");
        }

        if (token) {
          await fetchProfile();
        } else {
          setLoading(false);
        }
      } catch (err) {
        console.error("Auth error:", err);
        setLoading(false);
      }
    };

    initAuth();
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await api.get('/auth/me');
      const userData = res.data;
      setUser(userData);
      
      // role might be stored in uppercase or lowercase. Let's safely check
      if (!userData.role || userData.role.toLowerCase() === 'guest') {
        setNeedsRoleSelection(true);
      } else {
        setNeedsRoleSelection(false);
      }
    } catch (err) {
      console.error("Failed to fetch profile", err);
    } finally {
      setLoading(false);
    }
  };

  const selectRole = async (role) => {
    try {
      await api.post('/auth/select-role', { role });
      await fetchProfile(); // re-fetch to get updated role
    } catch (err) {
      console.error("Failed to select role", err);
      alert("Rol tanlashda xatolik yuz berdi");
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, needsRoleSelection, selectRole }}>
      {children}
    </AuthContext.Provider>
  );
};
