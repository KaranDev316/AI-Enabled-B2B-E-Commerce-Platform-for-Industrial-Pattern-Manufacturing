import React, { useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';
import './styles.css';

import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { CustomerPortal } from './pages/CustomerPortal';
import { EmployeePortal } from './pages/EmployeePortal';
import { AdminPortal } from './pages/AdminPortal';

import { CataloguePage } from './pages/CataloguePage';
import { LandingPage } from './pages/LandingPage';

function PublicNavigationScroll() {
  const { pathname, hash, key } = useLocation();
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView();
    else window.scrollTo(0, 0);
  }, [pathname, hash, key]);
  return null;
}

function NotFound() {
  return (
    <main className="container py-5 text-center">
      <h1 className="h3 mb-3">Page Not Found</h1>
      <p className="text-secondary mb-4">The requested portal route does not exist.</p>
      <Link to="/" className="btn btn-primary btn-sm">
        Return to Home
      </Link>
    </main>
  );
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <PublicNavigationScroll />
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/products" element={<CataloguePage />} />
          <Route path="/products/:productId" element={<CataloguePage />} />
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
