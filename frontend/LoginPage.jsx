import React, { useState, useEffect } from 'react';

function LoginPage() {
  const [initData, setInitData] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Telegram WebApp dan initData ni avtomatik olish
  useEffect(() => {
    if (window.Telegram && window.Telegram.WebApp) {
      const tg = window.Telegram.WebApp;
      tg.ready();
      tg.expand(); // Appni to'liq ekranga yoyish
      
      const data = tg.initData;
      if (data) {
        setInitData(data);
        // Avtomatik login qilish
        handleLogin(data);
      }
    }
  }, []);

  const handleLogin = async (dataToSubmit) => {
    setLoading(true);
    setError('');
    setResponse(null);
    try {
      const res = await fetch('/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ init_data: dataToSubmit }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Login failed');
      setResponse(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    handleLogin(initData);
  };

  return (
    <div style={{ maxWidth: 600, margin: '40px auto', padding: 24, border: '1px solid #eee', borderRadius: 8, fontFamily: 'sans-serif' }}>
      <h2 style={{ color: '#2c3e50' }}>Logistika - Telegram Login</h2>
      <p style={{ color: '#7f8c8d' }}>
        {window.Telegram?.WebApp?.initData 
          ? "Telegram orqali avtomatik aniqlandi ✅" 
          : "Telegram WebApp initData ni kiriting va serverdan javobni oling."}
      </p>
      
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 8, fontWeight: 'bold' }}>initData:</label>
          <textarea
            value={initData}
            onChange={e => setInitData(e.target.value)}
            placeholder="query_id=...&user=...&hash=..."
            style={{ width: '100%', padding: 12, minHeight: 120, borderRadius: 4, border: '1px solid #ccc', boxSizing: 'border-box' }}
            required
          />
        </div>
        <button 
          type="submit" 
          disabled={loading} 
          style={{ 
            width: '100%', 
            padding: 12, 
            backgroundColor: '#3498db', 
            color: 'white', 
            border: 'none', 
            borderRadius: 4, 
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: 16
          }}
        >
          {loading ? 'Yuborilmoqda...' : 'Loginni tekshirish'}
        </button>
      </form>

      {error && (
        <div style={{ color: '#e74c3c', marginTop: 16, padding: 12, backgroundColor: '#fadbd8', borderRadius: 4 }}>
          <strong>Xato:</strong> {error}
        </div>
      )}

      {response && (
        <div style={{ marginTop: 24 }}>
          <h4 style={{ color: '#27ae60' }}>✅ Server javobi:</h4>
          <pre style={{ 
            background: '#f8f9fa', 
            padding: 16, 
            borderRadius: 4, 
            border: '1px solid #e9ecef',
            overflowX: 'auto',
            fontSize: 14
          }}>
            {JSON.stringify(response, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

export default LoginPage;

