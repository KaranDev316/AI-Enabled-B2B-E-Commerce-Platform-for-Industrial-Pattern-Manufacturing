import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './LandingPage.css';
import './LoginPage.css';
import './RegisterPage.css';
import referenceImage from '../assets/landing-reference.webp';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export function RegisterPage() {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    company_name: '',
    contact_person: '',
    phone: '',
    gstin: '',
    address: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  function handleChange(e) {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'same-origin',
        body: JSON.stringify({
          email: formData.email,
          password: formData.password,
          company_name: formData.company_name,
          contact_person: formData.contact_person,
          phone: formData.phone,
          gstin: formData.gstin || null,
          address: formData.address || null,
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData?.detail?.message || 'Registration failed. Please check your details.');
      }

      setSuccess('Account registered successfully! Redirecting to sign in…');
      setTimeout(() => {
        navigate('/login', { state: { prefillEmail: formData.email } });
      }, 1500);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  const fields = [
    { name: 'company_name', label: 'Company name', placeholder: 'Apex Castings Ltd', autoComplete: 'organization', required: true },
    { name: 'contact_person', label: 'Contact person', placeholder: 'Your full name', autoComplete: 'name', required: true },
    { name: 'email', label: 'Work email address', placeholder: 'name@company.com', type: 'email', autoComplete: 'username', required: true },
    { name: 'phone', label: 'Phone / mobile number', placeholder: '+91 98765 43210', type: 'tel', autoComplete: 'tel', required: true },
    { name: 'gstin', label: 'GSTIN', placeholder: '24AAACA1234A1Z5', maxLength: 50 },
    { name: 'address', label: 'Factory / plant address', placeholder: 'Street, area, city', autoComplete: 'street-address' },
    { name: 'password', label: 'Password', placeholder: 'At least 8 characters', type: 'password', autoComplete: 'new-password', required: true, minLength: 8, maxLength: 128 },
    { name: 'confirmPassword', label: 'Confirm password', placeholder: 'Repeat your password', type: 'password', autoComplete: 'new-password', required: true, minLength: 8, maxLength: 128 },
  ];

  return (
    <div className="kpc-public login-page register-page">
      <header className="public-header"><div className="public-container public-header-inner">
        <Link className="public-logo" to="/" aria-label="Khodel Pattern Craft home"><strong><i>K</i>PC</strong><small>KHODEL PATTERN CRAFT</small></Link>
        <Link className="login-back" to="/">← Back to home</Link>
      </div></header>
      <main className="login-main">
        <div className="login-shell register-shell">
          <aside className="login-story" aria-labelledby="register-story-title">
            <p className="public-eyebrow">Precision. Reliability. Performance.</p>
            <h2 id="register-story-title">Your business.<br />Our <em>craft.</em></h2>
            <p>Create your customer account and bring your next pattern requirement to KPC.</p>
            <div className="login-pattern" role="img" aria-label="Precision machined metallic pattern"><img src={referenceImage} alt="" /></div>
            <ol className="register-benefits"><li><span>01</span>Share requirements and CAD drawings</li><li><span>02</span>Keep your submitted RFQs together</li><li><span>03</span>Connect with KPC through support</li></ol>
            <div className="login-story-footer"><span>WOODEN & METALLIC PATTERNS</span><span>Ahmedabad, Gujarat</span></div>
          </aside>
          <section className="login-form-panel" aria-labelledby="register-title">
            <p className="public-eyebrow">Get started with KPC</p>
            <h1 id="register-title">Create your business account</h1>
            <p className="login-intro">Tell us a little about your company. Your account is for customer access.</p>
            {error && <div className="login-error" id="register-error" role="alert">{error}</div>}
            {success && <div className="register-success" role="status">{success}</div>}
            <form onSubmit={handleSubmit} aria-busy={isSubmitting}>
              <p className="register-required">Fields marked <span aria-hidden="true">*</span> are required.</p>
              <div className="register-fields">
                {fields.map(field => <div className="login-field" key={field.name}>
                  <label htmlFor={field.name}>{field.label} {field.required ? <span className="register-asterisk" aria-hidden="true">*</span> : <span className="register-optional">(optional)</span>}</label>
                  <input id={field.name} name={field.name} type={field.type || 'text'} placeholder={field.placeholder} autoComplete={field.autoComplete} required={field.required} minLength={field.minLength} maxLength={field.maxLength} value={formData[field.name]} onChange={handleChange} disabled={isSubmitting || Boolean(success)} aria-describedby={error ? 'register-error' : undefined} />
                </div>)}
              </div>
              <button type="submit" className="public-button public-button-orange login-submit" disabled={isSubmitting || Boolean(success)}>{isSubmitting ? 'Creating your account…' : success ? 'Account created' : <>Create Business Account <span aria-hidden="true">→</span></>}</button>
            </form>
            <div className="login-register"><p>Already have a customer account?</p><Link to="/login">Sign in to your workspace <span aria-hidden="true">→</span></Link></div>
          </section>
        </div>
      </main>

    </div>
  );
}
