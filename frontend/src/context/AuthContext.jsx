import React, { createContext, useContext, useEffect, useState } from 'react';

const AuthContext = createContext(null);
const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export function AuthProvider({ children }) {
  // Initialize auth state directly from tab-isolated sessionStorage
  const [user, setUser] = useState(() => {
    try {
      const stored = sessionStorage.getItem('kpc_auth_user');
      return stored ? JSON.parse(stored) : null;
    } catch (_) {
      return null;
    }
  });

  const [csrfToken, setCsrfToken] = useState(() => {
    return sessionStorage.getItem('kpc_csrf_token') || null;
  });

  const [loading, setLoading] = useState(() => {
    // If no token exists in this tab's sessionStorage, it starts as unauthenticated immediately
    return typeof window !== 'undefined' ? !!sessionStorage.getItem('kpc_auth_token') : false;
  });

  const [error, setError] = useState(null);

  // Validate active session on initial mount ONLY if this tab has an active token
  useEffect(() => {
    let isMounted = true;
    const token = sessionStorage.getItem('kpc_auth_token');

    if (!token) {
      setLoading(false);
      return;
    }

    async function checkAuth() {
      try {
        const response = await fetch(`${API_BASE}/auth/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
            'Cache-Control': 'no-store, no-cache',
          },
        });

        if (response.ok) {
          const data = await response.json();
          if (isMounted) {
            setUser(data.user);
            setCsrfToken(data.csrf_token);
            sessionStorage.setItem('kpc_auth_user', JSON.stringify(data.user));
            sessionStorage.setItem('kpc_csrf_token', data.csrf_token);
            if (data.token || data.session_token) {
              sessionStorage.setItem('kpc_auth_token', data.token || data.session_token);
            }
          }
        } else {
          // Token is invalid or expired for this tab
          if (isMounted) {
            sessionStorage.removeItem('kpc_auth_token');
            sessionStorage.removeItem('kpc_auth_user');
            sessionStorage.removeItem('kpc_csrf_token');
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
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        const message = errData?.detail?.message || 'Login failed. Please check your credentials.';
        setError(message);
        throw new Error(message);
      }

      const data = await response.json();
      const token = data.token || data.session_token || '';

      // Persist strictly to this tab's sessionStorage
      sessionStorage.setItem('kpc_auth_token', token);
      sessionStorage.setItem('kpc_auth_user', JSON.stringify(data.user));
      sessionStorage.setItem('kpc_csrf_token', data.csrf_token);

      setUser(data.user);
      setCsrfToken(data.csrf_token);
      return data.user;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }

  async function logout() {
    const token = sessionStorage.getItem('kpc_auth_token');
    const tokenCsrf = sessionStorage.getItem('kpc_csrf_token') || csrfToken;

    try {
      await fetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: {
          'X-CSRF-Token': tokenCsrf || '',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      // Clear tab-isolated authentication state
      sessionStorage.removeItem('kpc_auth_token');
      sessionStorage.removeItem('kpc_auth_user');
      sessionStorage.removeItem('kpc_csrf_token');
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
