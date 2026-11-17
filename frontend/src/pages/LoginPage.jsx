import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './LandingPage.css';
import './LoginPage.css';
import referenceImage from '../assets/landing-reference.webp';

export function LoginPage() {
  const location = useLocation();
  const prefillEmail = location.state?.prefillEmail || '';

  const [email, setEmail] = useState(prefillEmail);
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState('');

  const { user, login } = useAuth();
  const navigate = useNavigate();

  const requested = location.state?.from;
  const from = requested?.pathname ? requested.pathname + (requested.search || '') : null;

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
    <div className="kpc-public login-page">
      <header className="public-header">
        <div className="public-container public-header-inner">
          <Link className="public-logo" to="/" aria-label="Khodel Pattern Craft home"><strong><i>K</i>PC</strong><small>KHODEL PATTERN CRAFT</small></Link>
          <Link className="login-back" to="/">← Back to home</Link>
        </div>
      </header>
      <main className="login-main">
        <div className="login-shell">
          <aside className="login-story" aria-labelledby="login-story-title">
            <p className="public-eyebrow">Precision. Reliability. Performance.</p>
            <h2 id="login-story-title">Your next pattern<br />starts <em>here.</em></h2>
            <p>From your first drawing to a finished pattern. Keep your requirements and conversations together in your KPC workspace.</p>
            <div className="login-pattern" role="img" aria-label="Precision machined metallic pattern"><img src={referenceImage} alt="" /></div>
            <div className="login-story-footer"><span>WOODEN & METALLIC PATTERNS</span><span>Ahmedabad, Gujarat</span></div>
          </aside>
          <section className="login-form-panel" aria-labelledby="login-title">
            <p className="public-eyebrow">Welcome to KPC</p>
            <h1 id="login-title">Sign in to your workspace</h1>
            <p className="login-intro">One secure sign-in for customers, employees, and Admin.</p>
            {localError && <div className="login-error" id="login-error" role="alert">{localError}</div>}
            <form onSubmit={handleSubmit} noValidate aria-busy={isSubmitting}>
              <div className="login-field">
                <label htmlFor="email">Work email address</label>
                <input id="email" type="email" placeholder="name@company.com" value={email} onChange={e => setEmail(e.target.value)} autoComplete="username" required disabled={isSubmitting} aria-describedby={localError ? 'login-error' : undefined} />
              </div>
              <div className="login-field">
                <label htmlFor="password">Password</label>
                <input id="password" type="password" placeholder="Enter your password" value={password} onChange={e => setPassword(e.target.value)} autoComplete="current-password" required disabled={isSubmitting} aria-describedby={localError ? 'login-error' : undefined} />
              </div>
              <button type="submit" className="public-button public-button-orange login-submit" disabled={isSubmitting}>
                {isSubmitting ? 'Signing in…' : <>Sign In <span aria-hidden="true">→</span></>}
              </button>
            </form>
            <div className="login-register"><p>New to Khodel Pattern Craft?</p><Link to="/register">Create a business account <span aria-hidden="true">→</span></Link></div>
            <p className="login-access-note">Your account takes you to the workspace assigned to your role.</p>
          </section>
        </div>
      </main>
      <footer className="login-footer"><span>Khodel Pattern Craft</span><span>Industrial pattern manufacturing · Ahmedabad, Gujarat</span></footer>
    </div>
  );
}
