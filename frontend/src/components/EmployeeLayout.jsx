import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { CustomerIcon } from './CustomerLayout';
import '../pages/CustomerPortal.css';
import '../pages/EmployeePortal.css';

export function EmployeeIcon({ name, ...props }) {
  if (name === 'issue') return <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}><path d="m12 3 10 18H2zM12 9v5M12 17h.01"/></svg>;
  return <CustomerIcon name={name === 'tasks' ? 'rfqs' : name === 'completed' ? 'check' : name} {...props}/>;
}

export const employeePages = [
  { id: 'dashboard', title: 'Dashboard', icon: 'dashboard', description: 'Here’s your work overview for today.' },
  { id: 'tasks', title: 'My Tasks', icon: 'tasks', description: 'View and manage your assigned jobs.' },
  { id: 'completed', title: 'Completed Jobs', icon: 'completed', description: 'View your finished jobs and their production details.' },
  { id: 'issue', title: 'Report Issue', icon: 'issue', description: 'Raise a production, machine, or material issue.' },
  { id: 'profile', title: 'My Profile', icon: 'profile', description: 'View and manage your personal and account details.' },
];

export function EmployeeLayout({ activeTab, onNavigate, profile, children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [compact, setCompact] = useState(() => window.matchMedia('(max-width: 760px)').matches);
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState('');
  const page = employeePages.find(p => p.id === activeTab) || employeePages[0];
  const name = profile.full_name || 'Employee';
  const initials = name.split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase();
  useEffect(() => {
    const media = window.matchMedia('(max-width: 760px)');
    const resize = () => { setCompact(media.matches); setMenuOpen(false); };
    const escape = event => { if (event.key === 'Escape') setMenuOpen(false); };
    media.addEventListener('change', resize); window.addEventListener('keydown', escape);
    return () => { media.removeEventListener('change', resize); window.removeEventListener('keydown', escape); };
  }, []);
  function go(tab) { onNavigate(tab); setMenuOpen(false); window.scrollTo(0, 0); }
  async function signOut() {
    setSigningOut(true); setError('');
    try { await logout(); navigate('/login'); }
    catch { setError('Unable to sign out. Please try again.'); }
    finally { setSigningOut(false); }
  }
  return <div className="customer-app employee-app">
    <a className="customer-skip" href="#employee-main">Skip to content</a>
    {menuOpen && <button className="customer-scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)}/>}
    <aside className={`customer-sidebar ${menuOpen ? 'is-open' : ''}`} id="employee-navigation" inert={compact && !menuOpen}>
      <Link className="customer-brand" to="/" aria-label="KPC home"><strong>KPC</strong><span>KHODEL PATTERN CRAFT</span></Link><p className="customer-portal-label">Employee Portal</p>
      <button className="employee-sidebar-person" onClick={() => go('profile')}><span className="employee-avatar">{initials}</span><span><strong>{name}</strong><small>{profile.department || 'Department not assigned'}</small><span className="employee-account-state"><i/>{user.is_active ? 'Active account' : 'Inactive account'}</span></span></button>
      <nav aria-label="Employee workspace">{employeePages.map(p => <button key={p.id} className={`customer-nav-item ${activeTab === p.id ? 'is-active' : ''}`} onClick={() => go(p.id)} aria-current={activeTab === p.id ? 'page' : undefined}><EmployeeIcon name={p.icon}/><span>{p.title}</span></button>)}</nav>
      <div className="customer-sidebar-bottom">{error && <p role="alert">{error}</p>}<button className="customer-logout" onClick={signOut} disabled={signingOut}><EmployeeIcon name="logout"/>{signingOut ? 'Signing out…' : 'Logout'}</button></div>
    </aside>
    <div className="customer-workspace"><header className="customer-topbar"><div className="employee-header-left"><button className="customer-menu-button" aria-label="Toggle employee navigation" aria-expanded={menuOpen} aria-controls="employee-navigation" onClick={() => setMenuOpen(!menuOpen)}><EmployeeIcon name="menu"/></button><span>Khodel Pattern Craft <span>/ Manufacturing</span></span></div><strong className="employee-header-label">EMPLOYEE PORTAL</strong></header>
      <main id="employee-main" className="customer-main employee-main">
        {activeTab !== 'dashboard' && <div className="customer-breadcrumb"><button onClick={() => go('dashboard')}>Home</button><span>›</span><span>{page.title}</span></div>}
        <div className="employee-page-heading"><div>{activeTab === 'dashboard' && <p className="employee-greeting">Hello, {name.split(' ')[0]}.</p>}<div className="employee-page-title">{activeTab !== 'dashboard' && <span className="employee-title-icon"><EmployeeIcon name={page.icon}/></span>}<div><h1>{page.title}</h1><p>{page.description}</p></div></div></div>{activeTab === 'dashboard' && <time dateTime={new Date().toISOString().slice(0, 10)}>{new Date().toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata' })}</time>}</div>
        {children}<footer className="customer-footer"><span>KPC Employee Portal</span><span>Khodel Pattern Craft</span></footer>
      </main>
    </div>
  </div>;
}
