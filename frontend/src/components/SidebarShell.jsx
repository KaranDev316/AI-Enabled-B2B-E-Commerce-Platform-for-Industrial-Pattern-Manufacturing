import React, { createContext, useContext, useEffect, useId, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './sidebar.css';

const SidebarContext = createContext(null);

export function SidebarMenuButton() {
  const menu = useContext(SidebarContext);
  if (!menu) return null;
  return <button ref={menu.toggle} type="button" className="kpc-menu-toggle" aria-label="Open navigation menu" aria-haspopup="dialog" aria-expanded={menu.open} aria-controls={menu.open ? menu.dialogId : undefined} onClick={() => menu.setOpen(true)}><span className="kpc-hamburger" aria-hidden="true"><i/><i/><i/></span><span>Menu</span></button>;
}

export function SidebarShell({ title = 'Explore KPC', items, activeSection, onSectionChange, children }) {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const dialogId = useId();
  const titleId = useId();
  const toggle = useRef(null);
  const drawer = useRef(null);
  const content = useRef(null);
  function close() { setOpen(false); }
  useEffect(() => setOpen(false), [location.pathname, location.search]);
  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    const wasInert = content.current?.inert;
    document.body.style.overflow = 'hidden';
    if (content.current) content.current.inert = true;
    drawer.current?.querySelector('button')?.focus();
    function onKey(e) {
      if (e.key === 'Escape') { e.preventDefault(); setOpen(false); }
      if (e.key !== 'Tab') return;
      const focusable = [...drawer.current.querySelectorAll('a[href],button:not([disabled])')];
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
    }
    document.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = previousOverflow;
      if (content.current) content.current.inert = wasInert || false;
      document.removeEventListener('keydown', onKey);
      toggle.current?.focus();
    };
  }, [open]);
  function select(item) {
    if (item.id && onSectionChange) onSectionChange(item.id);
    setOpen(false);
  }
  function isActive(item) {
    if (item.id) return item.id === activeSection;
    const [path, query = ''] = (item.to || '').split('?');
    if (query) return location.pathname === path && location.search === `?${query}`;
    if (path === '/catalogue') return (location.pathname === path && !location.search) || location.pathname.startsWith('/products/');
    return location.pathname === path && !location.search;
  }
  return <SidebarContext.Provider value={{open,setOpen,dialogId,toggle}}><div className="kpc-sidebar-shell">
    <div ref={content} className="kpc-sidebar-page">

      <div className="kpc-sidebar-content">{children}</div>
    </div>
    {open && <div className="kpc-drawer-layer"><div className="kpc-drawer-backdrop" aria-hidden="true" onClick={close}/><aside ref={drawer} id={dialogId} className="kpc-sidebar" role="dialog" aria-modal="true" aria-labelledby={titleId}>
      <div className="kpc-sidebar-heading"><Link className="kpc-sidebar-brand" to="/" onClick={close}>KPC<span>KHODEL PATTERN CRAFT</span></Link><button className="kpc-menu-close" aria-label="Close navigation menu" onClick={close}>×</button></div>
      <nav aria-label={title} className="kpc-side-navigation"><h2 id={titleId} className="kpc-sidebar-label">{title}</h2><ul>{items.map((item,index) => <li key={item.id || item.to}>{item.to ? <Link to={item.to} className={`kpc-side-link ${isActive(item) ? 'is-active' : ''}`} aria-current={isActive(item) ? 'page' : undefined} onClick={() => select(item)}><span className="kpc-side-number" aria-hidden="true">{String(index+1).padStart(2,'0')}</span><span>{item.label}</span><span className="kpc-side-arrow" aria-hidden="true">↗</span></Link> : <button type="button" className={`kpc-side-link ${isActive(item) ? 'is-active' : ''}`} aria-current={isActive(item) ? 'true' : undefined} onClick={() => select(item)}><span className="kpc-side-number" aria-hidden="true">{String(index+1).padStart(2,'0')}</span><span>{item.label}</span><span className="kpc-side-arrow" aria-hidden="true">→</span></button>}</li>)}</ul><div className="kpc-sidebar-note">Built around your requirements.<small>Patterns · People · Production</small></div></nav>
    </aside></div>}
  </div></SidebarContext.Provider>;
}
