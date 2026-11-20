import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export function CustomerIcon({ name, size = 21, ...props }) {
  const paths = {
    dashboard: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    rfqs: <><path d="M14 3H5v18h14V8zM14 3v6h5M8 13h8M8 17h5"/></>,
    orders: <><path d="m3 7 9-4 9 4v11l-9 4-9-4zM3 7l9 4 9-4M12 11v11M7 5l10 5"/></>,
    invoices: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 10h18M7 15h4M15 15h2"/></>,
    support: <><path d="M4 14v-3a8 8 0 0 1 16 0v3M20 18c0 3-4 3-7 3"/><rect x="2" y="11" width="5" height="7" rx="2"/><rect x="17" y="11" width="5" height="7" rx="2"/></>,
    profile: <><circle cx="12" cy="7" r="4"/><path d="M4 21v-2a8 8 0 0 1 16 0v2z"/></>,
    company: <><path d="M4 21V3h12v18M16 9h4v12H2M8 7h4M8 11h4M8 15h4M9 21v-3h3v3"/></>,
    upload: <><path d="M4 15v6h16v-6M12 16V3m-6 6 6-6 6 6"/></>,
    arrow: <path d="M4 12h16m-6-6 6 6-6 6"/>,
    logout: <><path d="M9 3H4v18h5M9 12h13m-5-5 5 5-5 5"/></>,
    menu: <path d="M3 6h18M3 12h18M3 18h18"/>,
    close: <path d="m5 5 14 14M5 19 19 5"/>,
    plus: <path d="M12 4v16M4 12h16"/>,
    search: <><circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    lock: <><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name] || paths.rfqs}</svg>;
}

export const customerPages = [
  { id: 'dashboard', title: 'Dashboard', icon: 'dashboard', description: 'Your requirements, conversations, and next steps in one place.' },
  { id: 'orders', title: 'My Orders', icon: 'orders', description: 'Review accepted orders, payment status, and cancellation history.' },
  { id: 'rfqs', title: 'Requests for Quotation', icon: 'rfqs', description: 'Share your requirements and keep track of every submitted request.' },
  { id: 'invoices', title: 'Invoices & Payments', icon: 'invoices', description: 'Your invoices and payment information, together.' },
  { id: 'support', title: 'Support & Complaints', icon: 'support', description: 'Get help with your requirements and continue your conversations with KPC.' },
  { id: 'profile', title: 'Business Profile', icon: 'profile', description: 'Manage your company details and account security.' },
];

export function CustomerLayout({ activeTab, onNavigate, company, onNewRfq, wizardOpen, children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [compact, setCompact] = useState(() => window.matchMedia('(max-width: 760px)').matches);
  const [signingOut, setSigningOut] = useState(false);
  const [logoutError, setLogoutError] = useState('');
  useEffect(() => {
    const media = window.matchMedia('(max-width: 760px)');
    const resize = () => { setCompact(media.matches); setMenuOpen(false); };
    const escape = event => { if (event.key === 'Escape') setMenuOpen(false); };
    media.addEventListener('change', resize);
    window.addEventListener('keydown', escape);
    return () => { media.removeEventListener('change', resize); window.removeEventListener('keydown', escape); };
  }, []);
  const currentPage = customerPages.find(p => p.id === activeTab) || customerPages[0];
  const page = wizardOpen ? { ...currentPage, title: 'New request for quotation', description: 'Tell us what you need. We’ll help turn your design into a manufacturing-ready pattern.' } : currentPage;
  const initials = (company || user.email).split(/\s+/).slice(0, 2).map(s => s[0]).join('').toUpperCase();
  function go(id) { onNavigate(id); setMenuOpen(false); }
  async function signOut() {
    setSigningOut(true); setLogoutError('');
    try { await logout(); navigate('/login'); }
    catch { setLogoutError('Could not sign out. Please try again.'); }
    finally { setSigningOut(false); }
  }
  return <div className="customer-app">
    <a className="customer-skip" href="#customer-main">Skip to content</a>
    {menuOpen && <button className="customer-scrim" aria-label="Close navigation" onClick={() => setMenuOpen(false)} />}
    <aside className={`customer-sidebar ${menuOpen ? 'is-open' : ''}`} id="customer-navigation" inert={compact && !menuOpen}>
      <Link to="/" className="customer-brand" aria-label="KPC home"><strong>K<span>P</span>C</strong><span>KHODEL PATTERN CRAFT</span></Link>
      <p className="customer-portal-label">Customer Portal</p>
      <nav aria-label="Customer workspace">{customerPages.map(p => <button key={p.id} className={`customer-nav-item ${(wizardOpen ? 'rfqs' : activeTab) === p.id ? 'is-active' : ''}`} aria-current={(wizardOpen ? 'rfqs' : activeTab) === p.id ? 'page' : undefined} onClick={() => go(p.id)}><CustomerIcon name={p.icon}/><span>{p.title}</span></button>)}</nav>
      <div className="customer-sidebar-bottom">{logoutError && <p role="alert">{logoutError}</p>}<button className="customer-logout" onClick={signOut} disabled={signingOut}><CustomerIcon name="logout"/>{signingOut ? 'Signing out…' : 'Logout'}</button></div>
    </aside>
    <div className="customer-workspace">
      <header className="customer-topbar"><div className="customer-topbar-left"><button className="customer-menu-button" aria-label="Toggle navigation" aria-expanded={menuOpen} aria-controls="customer-navigation" onClick={() => setMenuOpen(!menuOpen)}><CustomerIcon name={menuOpen ? 'close' : 'menu'}/></button><span className="customer-topbar-title"><span className="customer-heading-icon orange"><CustomerIcon name={page.icon}/></span>{activeTab === 'dashboard' && !wizardOpen ? <h1>Dashboard</h1> : <strong>{wizardOpen ? 'RFQ & CAD Upload' : page.title}</strong>}</span></div><button className="customer-account" onClick={() => go('profile')}><span className="customer-avatar">{initials}</span><span><strong>{company || 'Your business'}</strong><small>Customer account</small></span><span aria-hidden="true">⌄</span></button></header>
      <main id="customer-main" className="customer-main"><div className="customer-breadcrumb"><button onClick={() => go('dashboard')}>Home</button><span>/</span><span>{page.title}</span></div><div className={`customer-page-heading ${activeTab === 'dashboard' && !wizardOpen ? 'customer-dashboard-heading' : ''}`}><div><h1>{page.title}</h1><p>{page.description}</p></div>{!wizardOpen && ['dashboard','rfqs'].includes(activeTab) && <button className="btn btn-primary customer-new-rfq" onClick={onNewRfq}><CustomerIcon name="plus" size={19}/> New RFQ</button>}</div>{children}<footer className="customer-footer"><span>© {new Date().getFullYear()} Khodel Pattern Craft</span><span>Precision in every pattern.</span></footer></main>
    </div>
  </div>;
}
