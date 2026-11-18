import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import '../pages/LandingPage.css';
import './Footer.css';

export function Footer() {
  const { pathname } = useLocation();
  if (pathname === "/customer") return null;
  function backToTop() {
    window.scrollTo({ top: 0, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' });
  }
  return <footer className="kpc-public site-footer">
    <div className="public-container site-footer-main">
      <nav className="site-footer-links" aria-label="Footer">
        <section><h2>Quick links</h2><ul>{[['Home','/'],['Products','/products'],['Company','/#company'],['Contact','/#contact']].map(([label,to]) => <li key={label}><Link to={to}>{label}</Link></li>)}</ul></section>
        <section><h2>Products</h2><ul><li><Link to="/products">Wooden patterns</Link></li><li><Link to="/products">Metallic patterns</Link></li></ul></section>
      </nav>
      <section className="site-footer-contact"><h2>Reach us</h2><a href="https://wa.me/917922971570" target="_blank" rel="noopener noreferrer">Chat on WhatsApp <span aria-hidden="true">↗</span></a></section>
    </div>
    <div className="site-footer-bottom"><div className="public-container"><p>© {new Date().getFullYear()} Khodel Pattern Craft. All rights reserved.</p><div className="site-footer-legal"><Link to="/privacy">Privacy Policy</Link><Link to="/terms">Terms</Link></div><button type="button" onClick={backToTop}>Back to top ↑</button></div></div>
  </footer>;
}
