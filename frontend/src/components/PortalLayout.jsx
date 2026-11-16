import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function PortalLayout({ title, subtitle, roleBadgeColor = 'primary', children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <div className="d-flex flex-column min-vh-100 bg-light">
      {/* Top Navbar */}
      <nav className="navbar navbar-expand-lg navbar-dark bg-dark px-3 px-lg-4 shadow-sm border-bottom border-secondary">
        <div className="container-fluid">
          <Link className="navbar-brand d-flex align-items-center gap-2" to="/">
            <span className="fw-bold tracking-tight text-white fs-4">KPC</span>
            <span className="badge bg-warning text-dark text-uppercase small">Industrial</span>
          </Link>

          <div className="d-flex align-items-center gap-3">
            <span className="text-light small d-none d-md-inline">
              Signed in as: <strong className="text-white">{user?.email}</strong>
            </span>
            <span className={`badge bg-${roleBadgeColor} text-uppercase px-2 py-1`}>
              {user?.role}
            </span>
            <button
              onClick={handleLogout}
              className="btn btn-outline-light btn-sm ms-2"
              type="button"
            >
              Sign out
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="container-fluid py-4 flex-grow-1 px-3 px-lg-5">
        <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-center mb-4 pb-3 border-bottom">
          <div>
            <h1 className="h3 text-dark fw-bold mb-1">{title}</h1>
            {subtitle && <p className="text-muted small mb-0">{subtitle}</p>}
          </div>
          <div className="mt-2 mt-md-0">
            <span className="text-secondary small">
              Session Active · Server Verified
            </span>
          </div>
        </div>

        {children}
      </main>

      {/* Footer */}
      <footer className="footer py-3 bg-white border-top text-center text-muted small mt-auto px-3">
        <div className="container-fluid d-flex flex-column flex-md-row justify-content-between align-items-center gap-2">
          <span>KPC — Khodel Pattern Craft · Odhav GIDC, Ahmedabad, Gujarat · GSTIN: <strong className="font-monospace text-dark">24AAEFK7650C1ZM</strong></span>
          <span>B2B Industrial Pattern Manufacturing Platform</span>
        </div>
      </footer>
    </div>
  );
}
