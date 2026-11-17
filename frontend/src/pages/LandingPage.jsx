import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import referenceImage from '../assets/landing-reference.webp';
import './LandingPage.css';
import { downloadSpecifications } from '../data/downloadSpecifications';
import { PublicHeader } from '../components/PublicHeader';

export const patterns = [
  { title: 'Precision Wood Patterns', description: 'High-quality wooden patterns crafted for traditional casting molds.', detail: 'Share your casting application, dimensions, material preferences, and drawings. Our team reviews your requirement before preparing a quotation.', x: 103, y: 582, width: 208, height: 103, icon: 'layers' },
  { title: 'High-Tolerance Metal Patterns', description: 'Metallic patterns for repeatable industrial casting applications.', detail: 'Tell us about the part, required tolerances, quantity, and casting process. Include technical drawings so the team can review the specification.', x: 351, y: 582, width: 212, height: 103, icon: 'cube' },
  { title: 'Sand Casting Solutions', description: 'Purpose-built patterns shaped around your foundry’s requirements.', detail: 'Describe the casting method, shrinkage allowances, core box requirements, and surface finish you need. Final specifications are confirmed during quotation.', x: 604, y: 582, width: 209, height: 103, icon: 'box' },
  { title: 'Rapid Prototyping', description: 'Explore custom pattern requirements before moving into production.', detail: 'Bring your early-stage design or custom part requirement. Share a drawing and the intended application to discuss a suitable pattern with our team.', x: 858, y: 582, width: 206, height: 103, icon: 'gear' },
];
const steps = [
  { title: 'Upload CAD / RFQ', copy: 'Share your design and requirements securely.', icon: 'upload' },
  { title: 'Get Quotation', copy: 'Receive a detailed quote with lead time.', icon: 'document' },
  { title: 'Production', copy: 'Precision manufacturing with quality checks.', icon: 'gear' },
  { title: 'Delivery', copy: 'Your finished patterns, ready for the next step.', icon: 'truck' },
];

function Icon({ name, ...props }) {
  const paths = {
    upload: <><path d="M8 17H6a4 4 0 0 1-.7-7.9A7 7 0 0 1 19 8a4.5 4.5 0 0 1-.5 9H16"/><path d="m8 13 4-4 4 4M12 9v12"/></>,
    document: <><path d="M6 3h8l4 4v14H6zM14 3v5h4M9 12h6M9 16h6"/></>,
    gear: <><path d="m10 3-.5 3-2 .9L5 5.5 2.5 10l2.5 1.5v2L2.5 15 5 19.5l2.5-1.4 2 .9.5 3h5l.5-3 2-.9 2.5 1.4 2.5-4.5-2.5-1.5v-2L22.5 10 20 5.5l-2.5 1.4-2-.9L15 3z"/><circle cx="12.5" cy="12.5" r="3"/></>,
    truck: <><path d="M2 5h12v12H2zM14 9h4l4 4v4h-8M18 9v5h4"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="18" r="2"/></>,
    layers: <><path d="m3 8 9-5 9 5-9 5zM3 12l9 5 9-5M3 16l9 5 9-5"/></>,
    cube: <><path d="m12 2 9 5v10l-9 5-9-5V7zM3 7l9 5 9-5M12 12v10M7.5 4.5l9 5"/></>,
    box: <><path d="m3 9 9-5 9 5v11H3zM3 9l9 5 9-5M12 14v6"/><path d="M9 4V2h6v2"/></>,
    pin: <><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2"/></>,
    shield: <><path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6z"/><path d="m8 12 3 3 5-6"/></>,
    arrow: <path d="M4 12h16m-6-6 6 6-6 6"/>,
    menu: <path d="M3 6h18M3 12h18M3 18h18"/>,
    close: <path d="m5 5 14 14M5 19 19 5"/>,
  };
  return <svg width="24" height="24" viewBox="0 0 25 25" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{paths[name]}</svg>;
}

// Display only the artwork regions of the supplied reference; keep its source intact.
export function PatternArt({ crop, className = '', label }) {
  return <div className={`pattern-art ${className}`} role="img" aria-label={label} style={{ aspectRatio: `${crop.width} / ${crop.height}` }}>
    <img src={referenceImage} alt="" draggable="false" style={{ width: `${1536 / crop.width * 100}%`, left: `${-crop.x / crop.width * 100}%`, top: 0, transform: `translateY(${-crop.y / 1024 * 100}%)` }} />
  </div>;
}

export function LandingPage() {
  const { user } = useAuth();
  const [activeCard, setActiveCard] = useState(0);
  const cardsRef = useRef(null);
  const dialogRef = useRef(null);
  const [selectedPattern, setSelectedPattern] = useState(null);
  useEffect(() => { if (selectedPattern) dialogRef.current?.showModal(); }, [selectedPattern]);
  const specificationRows = selectedPattern ? [
    ['Pattern capability', selectedPattern.title],
    ['Material', selectedPattern.title.includes('Wood') ? 'Wood' : selectedPattern.title.includes('Metal') ? 'Metal' : 'To be confirmed'],
    ['Dimensions', 'Confirmed against your drawings'],
    ['Tolerance', 'To be confirmed during quotation'],
    ['Surface finish', 'To be confirmed during quotation'],
    ['Pattern weight', 'Depends on the agreed design'],
    ['Price and lead time', 'Provided in the official quotation'],
  ] : [];
  const portal = user ? `/${user.role}` : '/login';
  const quotePath = '/customer';

  function trackCard() {
    const rail = cardsRef.current;
    const cards = [...rail.children];
    const nearest = cards.reduce((best, card, index) => Math.abs(card.offsetLeft - rail.offsetLeft - rail.scrollLeft) < Math.abs(cards[best].offsetLeft - rail.offsetLeft - rail.scrollLeft) ? index : best, 0);
    setActiveCard(nearest);
  }

  return <div className="kpc-public">
    <a className="public-skip" href="#main-content">Skip to content</a>
    <PublicHeader />
    <main id="main-content">
      <section className="public-hero" id="home" aria-labelledby="hero-heading">
        <div className="public-container public-hero-inner">
          <div className="public-hero-copy">
            <p className="public-eyebrow">Precision. Reliability. Performance.</p>
            <h1 id="hero-heading">Precision Industrial<br className="desktop-break" /> Patterns, Delivered<br className="desktop-break" /> <em>On Time.</em></h1>
            <p className="public-hero-description">We manufacture high-precision wooden and metallic patterns for foundries. From CAD to casting-ready, we deliver quality you can trust.</p>
            <div className="public-hero-actions"><Link className="public-button public-button-orange" to={quotePath}><Icon name="upload" /> Upload Your CAD / RFQ</Link><Link className="public-button public-button-light" to="/products">View Catalogue</Link></div>
            <div className="public-proof">
              <div><Icon name="layers"/><p><strong>Wood & Metal</strong><span>Pattern manufacturing</span></p></div>
              <div><Icon name="document"/><p><strong>CAD to Pattern</strong><span>Built to your requirements</span></p></div>
              <div><Icon name="pin"/><p><strong>Ahmedabad</strong><span>Gujarat, India</span></p></div>
            </div>
          </div>
          <PatternArt className="public-hero-art" crop={{ x: 605, y: 76, width: 593, height: 424 }} label="Machined metallic industrial pattern with a cylindrical centre and four mounting holes" />
        </div>
      </section>
      <section className="public-capabilities public-container" id="capabilities" aria-labelledby="capabilities-heading">
        <div className="public-section-heading"><p className="public-eyebrow">What we manufacture</p><h2 id="capabilities-heading">Explore Our Pattern Capabilities</h2></div>
        <div className="public-pattern-grid" ref={cardsRef} onScroll={trackCard}>
          {patterns.map((pattern, i) => <article className="public-pattern-card" key={pattern.title} id={`pattern-${i}`}>
            <PatternArt crop={pattern} label={pattern.title} />
            <h3>{pattern.title}</h3><p>{pattern.description}</p>
            <button className="public-detail-link" onClick={() => setSelectedPattern(pattern)} aria-label={`View details: ${pattern.title}`}>View Details <Icon name="arrow" /></button>
          </article>)}
        </div>
        <div className="public-carousel-dots" aria-label="Choose a pattern capability">{patterns.map((pattern, i) => <button key={pattern.title} aria-label={`Show ${pattern.title}`} aria-pressed={activeCard === i} onClick={() => { const rail = cardsRef.current; rail.scrollTo({ left: rail.children[i].offsetLeft - rail.offsetLeft, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' }); }} />)}</div>
      </section>
      <section className="public-process" aria-labelledby="process-heading"><div className="public-container">
        <div className="public-section-heading"><p className="public-eyebrow">Our simple process</p><h2 id="process-heading">From CAD to Casting-Ready</h2></div>
        <ol className="public-process-list">{steps.map((step, i) => <li key={step.title}><div className="public-step-top"><span className="public-step-number">0{i + 1}</span><span className="public-step-icon"><Icon name={step.icon} /></span></div><div className="public-step-copy"><h3>{step.title}</h3><p>{step.copy}</p></div></li>)}</ol>
      </div></section>
      <section className="public-company public-container" id="company" aria-labelledby="company-heading" tabIndex={-1}>
        <div><p className="public-eyebrow">Company profile</p><h2 id="company-heading">Khodel Pattern Craft</h2><p className="public-company-tagline">Your pattern. Our craft.</p></div>
        <div><p>Based in Odhav, Ahmedabad, Khodel Pattern Craft manufactures industrial wooden and metallic patterns. We bring your drawings, specifications, and manufacturing requirements together in one clear quotation process.</p>
          <dl className="public-company-facts"><div><dt>Nature of work</dt><dd>Industrial pattern manufacturing</dd></div><div><dt>Products</dt><dd>Wooden and metallic patterns</dd></div><div><dt>GSTIN</dt><dd>24AAEFK7650C1ZM</dd></div></dl>
          <Link className="public-detail-link" to="/products">Explore our catalogue <Icon name="arrow" /></Link>
        </div>
      </section>
      <section className="public-contact" id="contact" aria-labelledby="contact-heading" tabIndex={-1}>
        <div className="public-container public-contact-grid"><div><p className="public-eyebrow">Contact Khodel Pattern Craft</p><h2 id="contact-heading">Let’s discuss your next pattern.</h2><p>Call our team or share your drawings through a quotation request.</p>
          <address className="public-contact-address"><strong>Visit us</strong><br />L/564, G.I.D.C. Estate, Odhav,<br />Ahmedabad – 382415, Gujarat, India</address>
        </div><div className="public-contact-actions"><div className="public-contact-phones"><span>Call our team</span><a href="tel:+917922971570">79229 71570</a><a href="tel:+919979231737">99792 31737</a></div><Link className="public-button public-button-orange" to={quotePath}>Get a Quote <Icon name="arrow" /></Link><Link to={user ? portal : '/register'}>{user ? 'Go to my portal' : 'New to KPC? Create an account'}</Link></div></div>
      </section>
    </main>
    <footer className="public-footer public-container"><Link className="public-logo" to="/" aria-label="Khodel Pattern Craft home"><strong><i>K</i>PC</strong><small>KHODEL PATTERN CRAFT</small></Link><p>Industrial pattern manufacturing<br/><span>Ahmedabad, Gujarat, India</span></p><a href="#home">Back to top ↑</a></footer>

    <dialog ref={dialogRef} className="public-pattern-dialog public-expanded-details" onClose={() => setSelectedPattern(null)} onClick={event => { if (event.target === event.currentTarget) event.currentTarget.close(); }} aria-labelledby="pattern-dialog-title">
      {selectedPattern && <>
        <button className="public-dialog-close" aria-label="Close pattern details" onClick={() => dialogRef.current.close()}><Icon name="close" /></button>
        <div className="public-detail-overview"><div><PatternArt crop={selectedPattern} label={selectedPattern.title} /><p className="public-detail-caption">Illustrative pattern image</p></div><section><p className="public-eyebrow">Pattern capabilities</p><h2 id="pattern-dialog-title">{selectedPattern.title}</h2><p>{selectedPattern.description}</p><dl>{specificationRows.slice(1).map(([label,value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl></section></div>
        <p className="public-detail-description">{selectedPattern.detail}</p>
        <Link className="public-button public-button-orange public-detail-action" to={quotePath}>Request for Quotation (RFQ) <Icon name="arrow" /></Link>
        <button className="public-button public-button-outline public-detail-action" onClick={() => downloadSpecifications(selectedPattern.title, specificationRows)}>Download PDF Specifications <span aria-hidden="true">↓</span></button>
        <p className="public-detail-caption">The PDF is a capability summary. Final specifications require confirmation in your quotation.</p>
      </>}
    </dialog>

  </div>;
}
