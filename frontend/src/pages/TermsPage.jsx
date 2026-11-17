import React from 'react';
import { Link } from 'react-router-dom';
import { PublicHeader } from '../components/PublicHeader';
import './PrivacyPage.css';

const sections = [
  {
    "title": "Purpose of this website",
    "paragraphs": [
      "This website is a final-year BCA project that demonstrates workflows for Khodel Pattern Craft (KPC), an industrial pattern manufacturer. The project team operates the demo for development, testing, and academic evaluation. Use the demo for those purposes under the access instructions given by the project team.",
      "Requests for quotation (RFQs), quotations, orders, invoices, delivery dates, and payment screens are simulations. Submitting or accepting anything through the demo creates no purchase, sale, production commitment, delivery obligation, or payment obligation. The demo does not take real payments."
    ]
  },
  {
    "title": "Accounts and acceptable use",
    "paragraphs": [
      "Use only your assigned test account or credentials the team has provided for shared testing. Keep individual credentials private and access only the accounts, records, and areas you are authorized to use. Do not access another user's files, bypass access controls, upload malicious files, or interfere with other users' access. Tell the team if your credentials are exposed or you can see records you should not be able to access."
    ]
  },
  {
    "title": "Information and files you submit",
    "paragraphs": [
      "Use synthetic data and sample files that you have permission to share. Keep real customer records, confidential drawings, government IDs, and payment credentials out of the demo. The team may use submitted sample material to test and demonstrate the relevant workflow. If you accidentally upload real or confidential information, contact the team promptly with the submission reference."
    ]
  },
  {
    "title": "Demonstration availability and privacy",
    "paragraphs": [
      "The team may reset test accounts and remove sample records during testing or after evaluation. Keep your own copy of any sample material you need. Sample prices, lead times, and automated estimates, where shown, are for demonstration only. See the academic Privacy Notice for information about demo records, cookies, and privacy requests."
    ]
  }
];

export function TermsPage() {
  return <div className="kpc-public"><PublicHeader /><main className="public-container privacy-page">
    <p className="public-eyebrow">Khodel Pattern Craft</p><h1>Terms of Use</h1>
    <p className="privacy-date">Academic demonstration · Effective <time dateTime="2026-11-17">17 November 2026</time></p>
    <p>Website: <a href="https://ai-enabled-b2-b-e-commerce-platform.vercel.app/">ai-enabled-b2-b-e-commerce-platform.vercel.app</a><br/>Project team contact: <a href="mailto:karanlicka@gmail.com">karanlicka@gmail.com</a></p>
    {sections.map((section,i) => <section key={section.title} aria-labelledby={`terms-section-${i}`}><h2 id={`terms-section-${i}`}>{section.title}</h2>{section.paragraphs.map(paragraph => <p key={paragraph}>{paragraph}</p>)}</section>)}
    <p>Read the <Link to="/privacy">Privacy Policy</Link> for the academic demonstration. For questions about these terms, email <a href="mailto:karanlicka@gmail.com">karanlicka@gmail.com</a>.</p>
  </main></div>;
}
