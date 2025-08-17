import React, { useState, useEffect } from 'react';
import LandingPage from './LandingPage';
import ChatAgent from './ChatAgent';
import './index.css';
import './ChatAgent.css';

function App() {
  const [jwt, setJwt] = useState(() => localStorage.getItem('jwt'));
  const [user, setUser] = useState(() => {
    const u = localStorage.getItem('user');
    try { return u ? JSON.parse(u) : null; } catch { return null; }
  });

  useEffect(() => {
    if (jwt && !user) {
      const u = localStorage.getItem('user');
      if (u) {
        try { setUser(JSON.parse(u)); } catch { /* ignore */ }
      }
    }
  }, [jwt, user]);

  const handleAuth = (token, userInfo) => {
    setJwt(token);
    setUser(userInfo);
    localStorage.setItem('jwt', token);
    localStorage.setItem('user', JSON.stringify(userInfo));
  };

  const handleLogout = () => {
    localStorage.removeItem('jwt');
    localStorage.removeItem('user');
    setJwt(null);
    setUser(null);
  };



  if (user) {
    return <ChatAgent user={user} onLogout={handleLogout} />;
  }

  return <LandingPage onAuth={handleAuth} />;
}

export default App;
