import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

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

  return (
    <div className="container py-5">
      <div className="row justify-content-center">
        <div className="col-12 col-lg-8">
          <div className="card shadow-sm border-0 rounded-4 p-4 p-md-5">
            <div className="text-center mb-4">
              <span className="brand d-block mb-1">KPC</span>
              <span className="text-uppercase small text-muted">Khodel Pattern Craft</span>
              <h2 className="h4 fw-bold mt-3">B2B Customer Registration</h2>
              <p className="text-secondary small">
                Register your business account to submit RFQs, upload CAD drawings, and track pattern manufacturing.
              </p>
            </div>

            {error && (
              <div className="alert alert-danger small py-2 px-3 mb-4" role="alert">
                {error}
              </div>
            )}

            {success && (
              <div className="alert alert-success small py-2 px-3 mb-4" role="alert">
                {success}
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate>
              <div className="row g-3">
                <div className="col-12 col-md-6">
                  <label className="form-label small fw-bold" htmlFor="company_name">
                    Company Name <span className="text-danger">*</span>
                  </label>
                  <input
                    id="company_name"
                    name="company_name"
                    type="text"
                    className="form-control"
                    placeholder="Apex Castings Ltd"
                    value={formData.company_name}
                    onChange={handleChange}
                    required
                    disabled={isSubmitting}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label small fw-bold" htmlFor="contact_person">
                    Contact Person Name <span className="text-danger">*</span>
                  </label>
                  <input
                    id="contact_person"
                    name="contact_person"
                    type="text"
                    className="form-control"
                    placeholder="Rajesh Patel"
                    value={formData.contact_person}
                    onChange={handleChange}
                    required
                    disabled={isSubmitting}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label small fw-bold" htmlFor="email">
                    Work Email Address <span className="text-danger">*</span>
                  </label>
                  <input
                    id="email"
                    name="email"
                    type="email"
                    className="form-control"
                    placeholder="procurement@foundry.com"
                    value={formData.email}
                    onChange={handleChange}
                    required
                    disabled={isSubmitting}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label small fw-bold" htmlFor="phone">
                    Phone / Mobile Number <span className="text-danger">*</span>
                  </label>
                  <input
                    id="phone"
                    name="phone"
                    type="tel"
                    className="form-control"
                    placeholder="+91 98765 43210"
                    value={formData.phone}
                    onChange={handleChange}
                    required
                    disabled={isSubmitting}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label small fw-bold" htmlFor="gstin">
                    GSTIN Number <span className="text-muted fw-normal">(Optional)</span>
                  </label>
                  <input
                    id="gstin"
                    name="gstin"
                    type="text"
                    className="form-control text-uppercase"
                    placeholder="24AAACA1234A1Z5"
                    value={formData.gstin}
                    onChange={handleChange}
                    disabled={isSubmitting}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label small fw-bold" htmlFor="address">
                    Factory / Plant Address
                  </label>
                  <input
                    id="address"
                    name="address"
                    type="text"
                    className="form-control"
                    placeholder="Plot 12, GIDC Vatva, Ahmedabad"
                    value={formData.address}
                    onChange={handleChange}
                    disabled={isSubmitting}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label small fw-bold" htmlFor="password">
                    Password <span className="text-danger">*</span>
                  </label>
                  <input
                    id="password"
                    name="password"
                    type="password"
                    className="form-control"
                    placeholder="Min 8 characters"
                    value={formData.password}
                    onChange={handleChange}
                    required
                    disabled={isSubmitting}
                  />
                </div>

                <div className="col-12 col-md-6">
                  <label className="form-label small fw-bold" htmlFor="confirmPassword">
                    Confirm Password <span className="text-danger">*</span>
                  </label>
                  <input
                    id="confirmPassword"
                    name="confirmPassword"
                    type="password"
                    className="form-control"
                    placeholder="Repeat password"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    required
                    disabled={isSubmitting}
                  />
                </div>
              </div>

              <div className="mt-4">
                <button
                  type="submit"
                  className="btn btn-primary btn-lg w-100 fw-bold"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? 'Registering Business Account…' : 'Complete B2B Registration'}
                </button>
              </div>
            </form>

            <div className="text-center mt-4 pt-3 border-top">
              <span className="text-secondary small">Already have a customer account? </span>
              <Link to="/login" className="small fw-bold">
                Sign In here →
              </Link>
            </div>
          </div>
          <div className="text-center text-muted small mt-3">
            Khodel Pattern Craft · Odhav GIDC, Ahmedabad · GSTIN: <span className="font-monospace fw-bold">24AAEFK7650C1ZM</span>
          </div>
        </div>
      </div>
    </div>
  );
}
