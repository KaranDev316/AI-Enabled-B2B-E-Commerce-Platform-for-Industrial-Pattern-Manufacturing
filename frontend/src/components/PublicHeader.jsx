import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './PublicHeader.css';

export function PublicHeader() {
  const { user } = useAuth();
  const { pathname, hash } = useLocation();
  const active = pathname.startsWith('/products') ? 'Products' : hash === '#company' ? 'Company' : hash === '#contact' ? 'Contact' : 'Home';
  const links = [['Home', '/'], ['Products', '/products'], ['Company', '/#company'], ['Contact', '/#contact']];
  return <header className="public-header public-site-header"><div className="public-container public-site-header-inner">
    <Link className="public-logo" to="/" aria-label="Khodel Pattern Craft home"><strong><i>K</i>PC</strong><small>KHODEL PATTERN CRAFT</small></Link>
    <nav className="public-site-navigation" aria-label="Main navigation">{links.map(([label,to]) => <Link key={label} to={to} aria-current={active === label ? 'page' : undefined}>{label}</Link>)}</nav>
    <div className="public-site-actions"><Link className="public-button public-button-outline" to={user ? `/${user.role}` : '/login'}>{user ? 'My Portal' : 'Login'}</Link><Link className="public-button public-button-orange" to="/customer">Get a Quote</Link></div>
  </div></header>;
}
