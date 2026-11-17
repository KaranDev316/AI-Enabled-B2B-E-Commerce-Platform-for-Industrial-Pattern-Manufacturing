import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function LoginPage() {
  const location = useLocation();
  const prefillEmail = location.state?.prefillEmail || '';

  const [email, setEmail] = useState(prefillEmail);
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState('');

  const { user, login } = useAuth();
  const navigate = useNavigate();

  const from = location.state?.from?.pathname || null;

  useEffect(() => {
    if (user) {
      if (from) {
        navigate(from, { replace: true });
      } else if (user.role === 'customer') {
        navigate('/customer', { replace: true });
      } else if (user.role === 'employee') {
        navigate('/employee', { replace: true });
      } else if (user.role === 'admin') {
        navigate('/admin', { replace: true });
      } else {
        navigate('/', { replace: true });
      }
    }
  }, [user, from, navigate]);

  async function handleSubmit(e) {
    e.preventDefault();
    setLocalError('');

    if (!email || !password) {
      setLocalError('Please enter both email and password.');
      return;
    }

    setIsSubmitting(true);
    try {
      const user = await login(email, password);
      if (from) {
        navigate(from, { replace: true });
      } else if (user.role === 'customer') {
        navigate('/customer', { replace: true });
      } else if (user.role === 'employee') {
        navigate('/employee', { replace: true });
      } else if (user.role === 'admin') {
        navigate('/admin', { replace: true });
      } else {
        navigate('/', { replace: true });
      }
    } catch (err) {
      setLocalError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="container py-5">
      <div className="row justify-content-center">
        <div className="col-12 col-md-8 col-lg-5">
          <div className="card shadow-sm border-0 rounded-4 p-4 p-md-5">
            <div className="text-center mb-4">
              <span className="brand d-block mb-1">KPC</span>
              <span className="text-uppercase small text-muted">
                Khodel Pattern Craft
              </span>
              <h2 className="h4 fw-bold mt-3">Portal Sign In</h2>
              <p className="text-secondary small">
                Sign in to access your Customer, Employee, or Admin workspace.
              </p>
            </div>

            {localError && (
              <div
                className="alert alert-danger d-flex align-items-center small py-2 px-3 mb-4"
                role="alert"
              >
                <div>{localError}</div>
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate>
              <div className="mb-3">
                <label className="form-label small fw-bold" htmlFor="email">
                  Work Email Address
                </label>
                <input
                  id="email"
                  type="email"
                  className="form-control form-control-lg fs-6"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="username"
                  required
                  disabled={isSubmitting}
                />
              </div>

              <div className="mb-4">
                <label className="form-label small fw-bold" htmlFor="password">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  className="form-control form-control-lg fs-6"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                  disabled={isSubmitting}
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary btn-lg w-100 fw-bold fs-6 shadow-sm mb-3"
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <span
                      className="spinner-border spinner-border-sm me-2"
                      role="status"
                      aria-hidden="true"
                    ></span>
                    Authenticating…
                  </>
                ) : (
                  'Sign In'
                )}
              </button>
            </form>

            <div className="card bg-light border-0 p-3 mt-3 text-center rounded-3">
              <p className="small text-secondary mb-2">New B2B Manufacturing Client?</p>
              <Link to="/register" className="btn btn-outline-primary btn-sm fw-bold">
                Register as B2B Customer →
              </Link>
            </div>

            <div className="text-center mt-3 pt-3 border-top">
              <Link to="/" className="text-decoration-none small text-secondary">
                ← Return to Public Workspace
              </Link>
            </div>
          </div>
          <div className="text-center text-muted small mt-3">
            Khodel Pattern Craft · Odhav GIDC, Ahmedabad · GSTIN: <span className="font-monospace fw-bold">24AAEFK7650C1ZM</span>
          </div>
        </div>
      </div>
    </div>
  );
}
