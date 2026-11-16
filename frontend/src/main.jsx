import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';
import './styles.css';

import { AuthProvider, useAuth } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { CustomerPortal } from './pages/CustomerPortal';
import { EmployeePortal } from './pages/EmployeePortal';
import { AdminPortal } from './pages/AdminPortal';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api';

function Workspace() {
  const [healthStatus, setHealthStatus] = useState('Checking API connection…');
  const { user, logout } = useAuth();

  useEffect(() => {
    const controller = new AbortController();
    async function checkConnection() {
      try {
        const response = await fetch(`${apiBaseUrl}/health`, {
          credentials: 'same-origin',
          signal: controller.signal,
        });
        if (!response.ok) throw new Error('API unavailable');
        const data = await response.json();
        if (data.status !== 'ok') throw new Error('Unexpected response');
        setHealthStatus('API connected. PostgreSQL-backed session authentication active.');
      } catch (error) {
        if (error.name !== 'AbortError') {
          setHealthStatus('API unavailable. Start the backend and refresh this page.');
        }
      }
    }
    checkConnection();
    return () => controller.abort();
  }, []);

  return (
    <main className="container py-5">
      <div className="workspace mx-auto p-4 p-md-5 shadow-sm">
        <div className="d-flex justify-content-between align-items-start mb-2">
          <div>
            <p className="brand mb-1">KPC</p>
            <p className="text-uppercase small text-muted">Khodel Pattern Craft</p>
          </div>
          {user ? (
            <div className="text-end">
              <span className="badge bg-primary text-uppercase me-2">{user.role}</span>
              <button onClick={logout} className="btn btn-outline-secondary btn-sm" type="button">
                Sign out
              </button>
            </div>
          ) : (
            <div className="d-flex gap-2">
              <Link to="/register" className="btn btn-outline-primary btn-sm px-3 fw-semibold">
                Register
              </Link>
              <Link to="/login" className="btn btn-primary btn-sm px-3 fw-semibold">
                Sign in
              </Link>
            </div>
          )}
        </div>

        <h1 className="h3 mt-4 text-dark fw-bold">B2B Manufacturing Platform Workspace</h1>
        <p className="text-secondary small">
          Final-year BCA project · Vertical Slices S01 & S02 (Registration & Account Access)
        </p>

        <p role="status" className="connection p-3 rounded small mb-4">
          {healthStatus}
        </p>

        {user ? (
          <div className="card bg-light border-0 p-3 mb-4">
            <h6 className="fw-bold mb-2">Active Session Verified:</h6>
            <p className="mb-2 small">
              Signed in as <strong>{user.email}</strong> (Role: <span className="text-uppercase fw-semibold">{user.role}</span>)
            </p>
            <div>
              {user.role === 'customer' && (
                <Link to="/customer" className="btn btn-primary btn-sm">
                  Go to Customer Workspace →
                </Link>
              )}
              {user.role === 'employee' && (
                <Link to="/employee" className="btn btn-info text-dark btn-sm">
                  Go to Employee Workspace →
                </Link>
              )}
              {user.role === 'admin' && (
                <Link to="/admin" className="btn btn-danger btn-sm">
                  Go to Admin Control Center →
                </Link>
              )}
            </div>
          </div>
        ) : (
          <div className="card bg-light border-0 p-3 mb-4">
            <h6 className="fw-bold mb-2">B2B Customer & Staff Portals:</h6>
            <p className="mb-3 small text-secondary">
              Role-protected portals are active for Customer, Employee, and Admin users with PostgreSQL-backed sessions, HttpOnly cookies, and Argon2id security.
            </p>
            <div className="d-flex gap-2">
              <Link to="/register" className="btn btn-primary btn-sm fw-bold">
                Register Business Account
              </Link>
              <Link to="/login" className="btn btn-outline-primary btn-sm">
                Sign In to Existing Account
              </Link>
            </div>
          </div>
        )}

        <div className="border-top pt-3 text-muted small d-flex flex-column flex-md-row justify-content-between align-items-center gap-2">
          <span>KPC — Khodel Pattern Craft · Odhav GIDC, Ahmedabad, Gujarat · GSTIN: <strong className="font-monospace text-dark">24AAEFK7650C1ZM</strong></span>
          <span className="text-secondary">Industrial Pattern Manufacturing &amp; Rapid Tooling</span>
        </div>
      </div>
    </main>
  );
}

function NotFound() {
  return (
    <main className="container py-5 text-center">
      <h1 className="h3 mb-3">Page Not Found</h1>
      <p className="text-secondary mb-4">The requested portal route does not exist.</p>
      <Link to="/" className="btn btn-primary btn-sm">
        Return to Workspace
      </Link>
    </main>
  );
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Workspace />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/customer"
            element={
              <ProtectedRoute allowedRoles={['customer']}>
                <CustomerPortal />
              </ProtectedRoute>
            }
          />
          <Route
            path="/employee"
            element={
              <ProtectedRoute allowedRoles={['employee']}>
                <EmployeePortal />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute allowedRoles={['admin']}>
                <AdminPortal />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </React.StrictMode>,
);
