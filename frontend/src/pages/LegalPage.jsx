import React from 'react';
import { Link } from 'react-router-dom';
import { PublicHeader } from '../components/PublicHeader';
export function LegalPage({ title }) {
  return <div className="kpc-public"><PublicHeader /><main className="public-container legal-placeholder"><p className="public-eyebrow">Khodel Pattern Craft</p><h1>{title}</h1><p>This page is a placeholder. The {title.toLowerCase()} is being prepared and has not been published yet.</p><p>For questions, please contact Khodel Pattern Craft directly.</p><Link className="public-detail-link" to="/#contact">Contact KPC →</Link></main></div>;
}
