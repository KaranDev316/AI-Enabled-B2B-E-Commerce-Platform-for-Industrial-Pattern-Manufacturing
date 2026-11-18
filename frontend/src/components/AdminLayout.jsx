import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { CustomerIcon as Icon } from './CustomerLayout';
import '../pages/CustomerPortal.css';
import '../pages/AdminPortal.css';

export const adminPages = [
  { id: 'dashboard', title: 'Admin Dashboard', label: 'Dashboard', icon: 'dashboard', description: 'Review requests, manage your catalogue, and act on open issues.' },
  { id: 'catalogue', title: 'Products', icon: 'orders', description: 'Manage catalogue products, categories, specifications, and images.' },
  { id: 'rfqs', title: 'RFQs & Quotations', icon: 'rfqs', description: 'Review customer requirements and their current status.' },
  { id: 'orders', title: 'Orders & Production', icon: 'company', description: 'Order management and production progress.' },
  { id: 'inventory', title: 'Inventory', icon: 'orders', description: 'Material quantities and stock adjustments.' },
  { id: 'invoices', title: 'Invoices & Payments', icon: 'invoices', description: 'Invoice and payment records.' },
  { id: 'support', title: 'Support Tickets', icon: 'support', description: 'Review customer conversations and resolve their issues.' },
  { id: 'users', title: 'Users', icon: 'profile', description: 'Manage customer and employee account access.' },
  { id: 'reports', title: 'Reports', icon: 'rfqs', description: 'Operational reports and summaries.' },
];

export function AdminLayout({ activeTab, onNavigate, search, onSearch, onPassword, children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [compact, setCompact] = useState(() => window.matchMedia('(max-width: 760px)').matches);
  const [logoutError, setLogoutError] = useState('');
  const [signingOut, setSigningOut] = useState(false);
  const page = adminPages.find(p => p.id === activeTab) || adminPages[0];
  useEffect(() => {
    const media = window.matchMedia('(max-width: 760px)');
    const resize = () => { setCompact(media.matches); setMenuOpen(false); };
    const escape = event => { if (event.key === 'Escape') setMenuOpen(false); };
    media.addEventListener('change', resize);
    window.addEventListener('keydown', escape);
    return () => { media.removeEventListener('change', resize); window.removeEventListener('keydown', escape); };
  }, []);
  function go(tab) { onNavigate(tab); setMenuOpen(false); window.scrollTo(0, 0); }
  async function signOut() {
    setSigningOut(true); setLogoutError('');
    try { await logout(); navigate('/login'); }
    catch { setLogoutError('Unable to sign out. Please try again.'); }
    finally { setSigningOut(false); }
  }
  return <div className="customer-app admin-app">
    <a href="#admin-main" className="customer-skip">Skip to content</a>
    {menuOpen && <button className="customer-scrim" onClick={() => setMenuOpen(false)} aria-label="Close navigation"/>}
    <aside className={`customer-sidebar ${menuOpen ? 'is-open' : ''}`} id="admin-navigation" inert={compact && !menuOpen}>
      <Link className="customer-brand" to="/" aria-label="KPC home"><strong><span className="admin-brand-k">K</span>PC</strong><span>KHODEL PATTERN CRAFT</span></Link>
      <p className="customer-portal-label">Admin Portal</p>
      <nav aria-label="Admin workspace">{adminPages.map(p => <button key={p.id} className={`customer-nav-item ${activeTab === p.id ? 'is-active' : ''}`} onClick={() => go(p.id)} aria-current={activeTab === p.id ? 'page' : undefined}><Icon name={p.icon} size={20}/><span>{p.label || p.title}</span></button>)}</nav>
      <div className="customer-sidebar-bottom"><div className="admin-identity"><span className="customer-avatar">AD</span><div><strong>Admin</strong><small>System Administrator</small></div></div>{logoutError && <p role="alert">{logoutError}</p>}<button className="customer-logout" onClick={signOut} disabled={signingOut}><Icon name="logout" size={18}/>{signingOut ? 'Signing out…' : 'Logout'}</button></div>
    </aside>
    <div className="customer-workspace">
      <header className="customer-topbar"><div className="admin-header-left"><button className="customer-menu-button" onClick={() => setMenuOpen(!menuOpen)} aria-controls="admin-navigation" aria-expanded={menuOpen} aria-label="Toggle Admin navigation"><Icon name="menu"/></button>{activeTab === 'dashboard' ? <label className="admin-dashboard-search"><Icon name="search" size={18}/><input value={search} onChange={e => onSearch(e.target.value)} placeholder="Search RFQs or support tickets…" aria-label="Search dashboard RFQs and support tickets"/></label> : <span className="admin-header-label">KPC / Administration</span>}</div><div className="admin-header-right"><button className="admin-support-link" aria-label="Open support tickets" onClick={() => go('support')}><Icon name="support"/></button><details className="admin-account-menu"><summary><span className="customer-avatar">AD</span><strong>Admin</strong><span aria-hidden="true">⌄</span></summary><div><span>{user?.email}</span><button onClick={onPassword}>Change password</button><Link to="/">Visit website</Link></div></details></div></header>
      <main className="customer-main admin-main" id="admin-main"><div className="admin-page-heading"><div><p>ADMIN PORTAL <span>/</span> {activeTab === 'dashboard' ? 'OVERVIEW' : page.title.toUpperCase()}</p><h1>{page.title}</h1><p>{page.description}</p></div><time dateTime={new Date().toISOString().slice(0, 10)}>{new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata' })}</time></div>{children}<footer className="customer-footer"><span>KPC Admin Portal</span><span>Khodel Pattern Craft</span></footer></main>
    </div>
  </div>;
}
