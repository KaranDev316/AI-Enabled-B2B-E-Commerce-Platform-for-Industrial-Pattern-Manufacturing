import React, { createContext, useContext, useEffect, useState } from 'react';

const AuthContext = createContext(null);
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [csrfToken, setCsrfToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check active session on initial mount
  useEffect(() => {
    let isMounted = true;

    async function checkAuth() {
      try {
        const response = await fetch(`${API_BASE}/auth/me`, {
          credentials: 'same-origin',
        });

        if (response.ok) {
          const data = await response.json();
          if (isMounted) {
            setUser(data.user);
            setCsrfToken(data.csrf_token);
          }
        } else {
          if (isMounted) {
            setUser(null);
            setCsrfToken(null);
          }
        }
      } catch (err) {
        if (isMounted) {
          setUser(null);
          setCsrfToken(null);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    checkAuth();
    return () => {
      isMounted = false;
    };
  }, []);

  async function login(email, password) {
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const message = errData?.detail?.message || 'Login failed. Please check your credentials.';
        setError(message);
        throw new Error(message);
      }

      const data = await response.json();
      setUser(data.user);
      setCsrfToken(data.csrf_token);
      return data.user;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }

  async function logout() {
    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: {
          'X-CSRF-Token': csrfToken || '',
        },
        credentials: 'same-origin',
      });
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      setUser(null);
      setCsrfToken(null);
      setError(null);
    }
  }

  return (
    <AuthContext.Provider value={{ user, csrfToken, loading, error, login, logout, setError }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
