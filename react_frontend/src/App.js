import React, { useState, useEffect } from 'react';
import logo from './logo.svg';
import './App.css';

// PUBLIC_INTERFACE
function App() {
  const [theme, setTheme] = useState('light');
  const [loading, setLoading] = useState(false);
  const [rxData, setRxData] = useState(null);
  const [error, setError] = useState(null);

  const apiBase = process.env.REACT_APP_API_BASE || 'http://localhost:8000';

  // Effect to apply theme to document element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // PUBLIC_INTERFACE
  const toggleTheme = () => {
    setTheme(prevTheme => prevTheme === 'light' ? 'dark' : 'light');
  };

  const fetchRx = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/api/rx-signal`);
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text}`);
      }
      const data = await res.json();
      setRxData(data);
      if (data.error) {
        setError(data.error);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRx();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="App">
      <header className="App-header">
        <button 
          className="theme-toggle" 
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
        >
          {theme === 'light' ? '🌙 Dark' : '☀️ Light'}
        </button>
        <img src={logo} className="App-logo" alt="logo" />
        <p style={{ marginTop: 16 }}>
          Telnet rx-signal monitor
        </p>
        <div style={{ marginTop: 12 }}>
          {loading ? (
            <p>Loading...</p>
          ) : (
            <>
              <p>
                Path: <strong>{rxData?.path || '1/1/3/2/1'}</strong>
              </p>
              <p>
                rx-signal: <strong>{rxData?.rx_signal ?? '—'}</strong> dBm
              </p>
              <p style={{ fontSize: 12, opacity: 0.8 }}>
                {rxData?.timestamp ? `Updated: ${rxData.timestamp}` : ''}
              </p>
              {error && (
                <p style={{ color: '#EF4444' }}>
                  {error}
                </p>
              )}
            </>
          )}
        </div>
        <button
          style={{
            marginTop: 16,
            backgroundColor: 'var(--button-bg)',
            color: 'var(--button-text)',
            border: 'none',
            borderRadius: 8,
            padding: '10px 20px',
            fontSize: 14,
            fontWeight: 600,
            cursor: 'pointer'
          }}
          onClick={fetchRx}
          aria-label="Refresh rx-signal"
        >
          Refresh
        </button>
      </header>
    </div>
  );
}

export default App;
