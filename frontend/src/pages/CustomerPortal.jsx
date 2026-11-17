import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { PortalLayout } from '../components/PortalLayout';
import { PasswordChangeModal } from '../components/PasswordChangeModal';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export function CustomerPortal() {
  const { user, csrfToken } = useAuth();
  const [profile, setProfile] = useState(user?.customer_profile || {});
  const [activeTab, setActiveTab] = useState('rfqs'); // 'rfqs', 'profile'

  // Profile Edit State
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({
    company_name: profile?.company_name || '',
    contact_person: profile?.contact_person || '',
    phone: profile?.phone || '',
    gstin: profile?.gstin || '',
    address: profile?.address || '',
  });

  // Password Modal
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [feedback, setFeedback] = useState({ error: '', success: '' });

  // RFQ Workflow State (Slice S05 & S06)
  const [myRfqs, setMyRfqs] = useState([]);
  const [loadingRfqs, setLoadingRfqs] = useState(false);
  const [isRfqModalOpen, setIsRfqModalOpen] = useState(false);
  const [selectedRfqDetail, setSelectedRfqDetail] = useState(null);
  const [catalogueProducts, setCatalogueProducts] = useState([]);

  const location = useLocation();
  useEffect(() => {
    const selected = new URLSearchParams(location.search).get('product');
    if (!selected || !catalogueProducts.length) return;
    const product = catalogueProducts.find(p => String(p.id) === selected);
    if (!product) return;
    setRfqForm(prev => ({ ...prev, rfq_type: 'standard', product_id: String(product.id), title: product.name, material: product.material_type || prev.material }));
    setRfqStep(1);
    setIsRfqModalOpen(true);
  }, [location.search, catalogueProducts]);

  // File Attachments State (Slice S06)
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [fileUploadError, setFileUploadError] = useState('');
  const [previewFile, setPreviewFile] = useState(null);
  const [isAttachingExtraFile, setIsAttachingExtraFile] = useState(false);
  const [extraFileError, setExtraFileError] = useState('');

  // RFQ Submission Form State
  const [rfqStep, setRfqStep] = useState(1);
  const [submittingRfq, setSubmittingRfq] = useState(false);
  const [rfqForm, setRfqForm] = useState({
    title: '',
    rfq_type: 'custom',
    product_id: '',
    material: 'Teak Wood',
    quantity: 1,
    description: '',
    dimensions: '',
    specifications: '',
    target_delivery_date: '',
    notes: '',
  });

  // Support & Inquiries State (Slice S14)
  const [supportTickets, setSupportTickets] = useState([]);
  const [loadingTickets, setLoadingTickets] = useState(false);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [isTicketModalOpen, setIsTicketModalOpen] = useState(false);
  const [isTicketDetailOpen, setIsTicketDetailOpen] = useState(false);
  const [customerContext, setCustomerContext] = useState({ orders: [], rfqs: [] });
  const [ticketForm, setTicketForm] = useState({
    ticket_type: 'inquiry',
    subject: '',
    message: '',
    order_id: '',
    rfq_id: '',
  });
  const [ticketFiles, setTicketFiles] = useState([]);
  const [ticketFileError, setTicketFileError] = useState('');
  const [submittingTicket, setSubmittingTicket] = useState(false);
  const [newReply, setNewReply] = useState('');
  const [ticketReplyFile, setTicketReplyFile] = useState(null);
  const [submittingReply, setSubmittingReply] = useState(false);
  const [ticketStatusFilter, setTicketStatusFilter] = useState('all');
  const [ticketTypeFilter, setTicketTypeFilter] = useState('all');

  useEffect(() => {
    fetchMyRfqs();
    fetchCatalogueProducts();
  }, []);

  async function fetchMyRfqs() {
    setLoadingRfqs(true);
    try {
      const res = await fetch(`${API_BASE}/rfqs/my`, { credentials: 'same-origin' });
      if (res.ok) {
        const data = await res.json();
        setMyRfqs(data);
      }
    } catch (err) {
      console.error('Failed to load RFQs:', err);
    } finally {
      setLoadingRfqs(false);
    }
  }

  async function fetchCatalogueProducts() {
    try {
      const res = await fetch(`${API_BASE}/products`, { credentials: 'same-origin' });
      if (res.ok) {
        const data = await res.json();
        setCatalogueProducts(data);
      }
    } catch (err) {
      console.error('Failed to load products:', err);
    }
  }

  async function fetchSupportTickets() {
    setLoadingTickets(true);
    try {
      const res = await fetch(`${API_BASE}/support/tickets/my`, { credentials: 'same-origin' });
      if (res.ok) {
        const data = await res.json();
        setSupportTickets(data);
      }
    } catch (err) {
      console.error('Failed to load support tickets:', err);
    } finally {
      setLoadingTickets(false);
    }
  }

  async function fetchCustomerContext() {
    try {
      const res = await fetch(`${API_BASE}/support/customer-context`, { credentials: 'same-origin' });
      if (res.ok) {
        const data = await res.json();
        setCustomerContext(data);
      }
    } catch (err) {
      console.error('Failed to load customer context:', err);
    }
  }

  async function handleOpenTicket(ticketId) {
    try {
      const res = await fetch(`${API_BASE}/support/tickets/${ticketId}`, { credentials: 'same-origin' });
      if (res.ok) {
        const data = await res.json();
        setSelectedTicket(data);
        setIsTicketDetailOpen(true);
        setNewReply('');
        setTicketReplyFile(null);
      } else {
        const err = await res.json().catch(() => ({}));
        setFeedback({ error: err.detail || 'Failed to open ticket.', success: '' });
      }
    } catch (err) {
      setFeedback({ error: 'Failed to retrieve ticket conversation.', success: '' });
    }
  }

  async function handleCreateTicket(e) {
    e.preventDefault();
    setSubmittingTicket(true);
    setTicketFileError('');

    try {
      const payload = {
        ticket_type: ticketForm.ticket_type,
        subject: ticketForm.subject,
        message: ticketForm.message,
        order_id: ticketForm.order_id ? parseInt(ticketForm.order_id, 10) : null,
        rfq_id: ticketForm.rfq_id ? parseInt(ticketForm.rfq_id, 10) : null,
      };

      const res = await fetch(`${API_BASE}/support/tickets`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken || '',
        },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to create support ticket.');
      }

      const created = await res.json();

      // If user selected attachments, upload each
      for (const file of ticketFiles) {
        const formData = new FormData();
        formData.append('file', file);
        const upRes = await fetch(`${API_BASE}/support/tickets/${created.id}/files`, {
          method: 'POST',
          headers: {
            'X-CSRF-Token': csrfToken || '',
          },
          credentials: 'same-origin',
          body: formData,
        });
        if (!upRes.ok) {
          const upErr = await upRes.json().catch(() => ({}));
          console.warn('File upload warning:', upErr.detail);
        }
      }

      setFeedback({
        error: '',
        success: `Support Ticket ${created.ticket_number} created successfully! Our team will respond shortly.`,
      });
      setIsTicketModalOpen(false);
      setTicketForm({ ticket_type: 'inquiry', subject: '', message: '', order_id: '', rfq_id: '' });
      setTicketFiles([]);
      fetchSupportTickets();
    } catch (err) {
      setTicketFileError(err.message);
    } finally {
      setSubmittingTicket(false);
    }
  }

  async function handleSendTicketReply(e) {
    e.preventDefault();
    if (!newReply.trim() || !selectedTicket) return;

    setSubmittingReply(true);
    try {
      const res = await fetch(`${API_BASE}/support/tickets/${selectedTicket.id}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken || '',
        },
        credentials: 'same-origin',
        body: JSON.stringify({ message: newReply.trim() }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to post message.');
      }

      // If reply attachment is provided
      if (ticketReplyFile) {
        const formData = new FormData();
        formData.append('file', ticketReplyFile);
        await fetch(`${API_BASE}/support/tickets/${selectedTicket.id}/files`, {
          method: 'POST',
          headers: {
            'X-CSRF-Token': csrfToken || '',
          },
          credentials: 'same-origin',
          body: formData,
        });
        setTicketReplyFile(null);
      }

      setNewReply('');
      // Refresh current ticket
      await handleOpenTicket(selectedTicket.id);
      fetchSupportTickets();
    } catch (err) {
      alert(err.message);
    } finally {
      setSubmittingReply(false);
    }
  }

  function handleProfileInputChange(e) {
    const { name, value } = e.target;
    setEditData((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSaveProfile(e) {
    e.preventDefault();
    setFeedback({ error: '', success: '' });
    setSaveLoading(true);

    try {
      const response = await fetch(`${API_BASE}/profile/me`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken || '',
        },
        credentials: 'same-origin',
        body: JSON.stringify(editData),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err?.detail?.message || 'Failed to update profile.');
      }

      const updatedUser = await response.json();
      setProfile(updatedUser.customer_profile);
      setIsEditing(false);
      setFeedback({ error: '', success: 'Business profile updated successfully!' });
    } catch (err) {
      setFeedback({ error: err.message, success: '' });
    } finally {
      setSaveLoading(false);
    }
  }

  function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  function getFileExtension(filename) {
    return filename ? filename.slice((filename.lastIndexOf('.') - 1 >>> 0) + 2).toUpperCase() : '';
  }

  function handleFileSelect(e) {
    setFileUploadError('');
    const files = Array.from(e.target.files);
    if (!files || files.length === 0) return;

    const allowedExts = ['.pdf', '.png', '.jpg', '.jpeg', '.webp', '.step', '.stp', '.iges', '.igs', '.stl', '.dwg', '.dxf'];
    const maxSize = 20 * 1024 * 1024;

    if (selectedFiles.length + files.length > 2) {
      setFileUploadError('Maximum 2 files can be attached per RFQ.');
      return;
    }

    const validNewFiles = [];
    for (const file of files) {
      const ext = '.' + file.name.split('.').pop().toLowerCase();
      if (!allowedExts.includes(ext)) {
        setFileUploadError(`File "${file.name}" has unsupported format. Allowed: PDF, PNG, JPG, WEBP, STEP, IGES, STL, DWG, DXF.`);
        return;
      }
      if (file.size > maxSize) {
        setFileUploadError(`File "${file.name}" exceeds the 20 MB size limit.`);
        return;
      }
      if (file.size === 0) {
        setFileUploadError(`File "${file.name}" is empty (0 bytes).`);
        return;
      }
      validNewFiles.push(file);
    }

    setSelectedFiles([...selectedFiles, ...validNewFiles]);
    e.target.value = '';
  }

  function handleRemoveSelectedFile(index) {
    setSelectedFiles(selectedFiles.filter((_, i) => i !== index));
  }

  async function handleUploadExtraFile(rfqId, file) {
    if (!file) return;
    setExtraFileError('');
    setIsAttachingExtraFile(true);

    const allowedExts = ['.pdf', '.png', '.jpg', '.jpeg', '.webp', '.step', '.stp', '.iges', '.igs', '.stl', '.dwg', '.dxf'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!allowedExts.includes(ext)) {
      setExtraFileError(`File "${file.name}" has unsupported format.`);
      setIsAttachingExtraFile(false);
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      setExtraFileError(`File "${file.name}" exceeds 20 MB limit.`);
      setIsAttachingExtraFile(false);
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API_BASE}/rfqs/${rfqId}/files`, {
        method: 'POST',
        headers: {
          'X-CSRF-Token': csrfToken || '',
        },
        credentials: 'same-origin',
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail?.message || 'Failed to upload attachment.');
      }

      await openRfqDetails(rfqId);
      fetchMyRfqs();
    } catch (err) {
      setExtraFileError(err.message);
    } finally {
      setIsAttachingExtraFile(false);
    }
  }

  async function handleDeleteAttachedFile(rfqId, fileId) {
    if (!window.confirm('Are you sure you want to remove this attached file?')) return;
    try {
      const res = await fetch(`${API_BASE}/rfqs/${rfqId}/files/${fileId}`, {
        method: 'DELETE',
        headers: {
          'X-CSRF-Token': csrfToken || '',
        },
        credentials: 'same-origin',
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail?.message || 'Failed to delete file.');
      }
      await openRfqDetails(rfqId);
      fetchMyRfqs();
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleRfqSubmit(e) {
    e.preventDefault();
    setFeedback({ error: '', success: '' });
    setSubmittingRfq(true);

    const payload = {
      title: rfqForm.title,
      rfq_type: rfqForm.rfq_type,
      product_id: rfqForm.rfq_type === 'standard' && rfqForm.product_id ? Number(rfqForm.product_id) : null,
      material: rfqForm.material,
      quantity: Number(rfqForm.quantity),
      description: rfqForm.description || null,
      dimensions: rfqForm.dimensions || null,
      specifications: rfqForm.specifications || null,
      target_delivery_date: rfqForm.target_delivery_date || null,
      notes: rfqForm.notes || null,
    };

    try {
      const response = await fetch(`${API_BASE}/rfqs`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken || '',
        },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err?.detail?.message || 'RFQ submission failed.');
      }

      const createdRfq = await response.json();

      // Upload any selected files
      if (selectedFiles.length > 0) {
        for (const file of selectedFiles) {
          const formData = new FormData();
          formData.append('file', file);
          const upRes = await fetch(`${API_BASE}/rfqs/${createdRfq.id}/files`, {
            method: 'POST',
            headers: {
              'X-CSRF-Token': csrfToken || '',
            },
            credentials: 'same-origin',
            body: formData,
          });
          if (!upRes.ok) {
            console.error('File upload failed for', file.name);
          }
        }
      }

      setFeedback({
        error: '',
        success: `RFQ ${createdRfq.rfq_number} submitted successfully with ${selectedFiles.length} file(s)! KPC Admin will review your pattern requirements.`,
      });
      setIsRfqModalOpen(false);
      setSelectedFiles([]);
      setFileUploadError('');
      setRfqStep(1);
      setRfqForm({
        title: '',
        rfq_type: 'custom',
        product_id: '',
        material: 'Teak Wood',
        quantity: 1,
        description: '',
        dimensions: '',
        specifications: '',
        target_delivery_date: '',
        notes: '',
      });
      fetchMyRfqs();
    } catch (err) {
      setFeedback({ error: err.message, success: '' });
    } finally {
      setSubmittingRfq(false);
    }
  }

  async function openRfqDetails(rfqId) {
    try {
      const res = await fetch(`${API_BASE}/rfqs/${rfqId}`, { credentials: 'same-origin' });
      if (res.ok) {
        const data = await res.json();
        setSelectedRfqDetail(data);
      }
    } catch (err) {
      console.error('Error fetching RFQ detail:', err);
    }
  }

  return (
    <PortalLayout
      title="Customer Workspace"
      subtitle="B2B Manufacturing Requirement Portal · Khodel Pattern Craft"
      roleBadgeColor="primary"
    >
      {user?.must_change_password && (
        <div className="alert alert-warning border-warning shadow-sm rounded-3 mb-4 d-flex justify-content-between align-items-center">
          <div>
            <strong>Password Update Required:</strong> You are currently using an assigned temporary password. Please update your password to secure your account.
          </div>
          <button
            onClick={() => setIsPasswordModalOpen(true)}
            className="btn btn-warning btn-sm fw-bold ms-3"
          >
            Change Password Now
          </button>
        </div>
      )}

      {feedback.success && (
        <div className="alert alert-success alert-dismissible fade show small py-2" role="alert">
          {feedback.success}
          <button
            type="button"
            className="btn-close"
            onClick={() => setFeedback({ ...feedback, success: '' })}
          ></button>
        </div>
      )}

      {feedback.error && (
        <div className="alert alert-danger alert-dismissible fade show small py-2" role="alert">
          {feedback.error}
          <button
            type="button"
            className="btn-close"
            onClick={() => setFeedback({ ...feedback, error: '' })}
          ></button>
        </div>
      )}

      {/* Navigation Tabs */}
      <ul className="nav nav-pills mb-4 gap-2">
        <li className="nav-item">
          <button
            className={`nav-link fw-bold btn-sm ${activeTab === 'rfqs' ? 'active' : 'bg-white border'}`}
            onClick={() => setActiveTab('rfqs')}
          >
            RFQs & Pattern Requirements (S05)
          </button>
        </li>
        <li className="nav-item">
          <button
            className={`nav-link fw-bold btn-sm ${activeTab === 'profile' ? 'active' : 'bg-white border'}`}
            onClick={() => setActiveTab('profile')}
          >
            Company Profile & Account Details (S02)
          </button>
        </li>
        <li className="nav-item">
          <button
            className={`nav-link fw-bold btn-sm ${activeTab === 'support' ? 'active' : 'bg-white border'}`}
            onClick={() => {
              setActiveTab('support');
              fetchSupportTickets();
              fetchCustomerContext();
            }}
          >
            Support & Inquiries (Slice S14)
          </button>
        </li>
      </ul>

      {/* TAB 1: RFQ WORKSPACE (SLICE S05) */}
      {activeTab === 'rfqs' && (
        <div>
          <div className="card shadow-sm border-0 rounded-3 mb-4">
            <div className="card-header bg-white border-bottom py-3 d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
              <div>
                <h5 className="card-title h6 mb-1 fw-bold">My Submitted Pattern RFQs</h5>
                <p className="text-muted small mb-0">
                  Track requirements submitted to KPC Engineering for Wooden & Metallic industrial pattern manufacturing.
                </p>
              </div>
              <button
                onClick={() => {
                  setRfqStep(1);
                  setIsRfqModalOpen(true);
                }}
                className="btn btn-primary btn-sm fw-bold px-3"
              >
                + Submit New RFQ
              </button>
            </div>

            <div className="table-responsive">
              <table className="table table-hover align-middle mb-0">
                <thead className="table-light small">
                  <tr>
                    <th>RFQ Reference</th>
                    <th>Type</th>
                    <th>Pattern / Part Title</th>
                    <th>Material</th>
                    <th>Quantity</th>
                    <th>Submitted On</th>
                    <th>Status</th>
                    <th className="text-end">Actions</th>
                  </tr>
                </thead>
                <tbody className="small">
                  {loadingRfqs ? (
                    <tr>
                      <td colSpan="8" className="text-center py-4 text-muted">
                        Loading your submitted requirements…
                      </td>
                    </tr>
                  ) : myRfqs.length === 0 ? (
                    <tr>
                      <td colSpan="8" className="text-center py-5 text-muted">
                        <p className="mb-2">You haven't submitted any RFQs yet.</p>
                        <button
                          onClick={() => setIsRfqModalOpen(true)}
                          className="btn btn-outline-primary btn-sm"
                        >
                          Create Your First Pattern RFQ →
                        </button>
                      </td>
                    </tr>
                  ) : (
                    myRfqs.map((rfq) => (
                      <tr key={rfq.id}>
                        <td>
                          <span className="fw-bold text-dark">{rfq.rfq_number}</span>
                        </td>
                        <td>
                          <span
                            className={`badge text-uppercase ${
                              rfq.rfq_type === 'standard' ? 'bg-secondary' : 'bg-primary'
                            }`}
                          >
                            {rfq.rfq_type}
                          </span>
                        </td>
                        <td className="fw-semibold text-dark">{rfq.title}</td>
                        <td>{rfq.material}</td>
                        <td>
                          <span className="badge bg-light text-dark border">
                            {rfq.quantity} pcs
                          </span>
                        </td>
                        <td className="text-muted">
                          {new Date(rfq.created_at).toLocaleDateString()}
                        </td>
                        <td>
                          <span
                            className={`badge text-uppercase ${
                              rfq.status === 'submitted'
                                ? 'bg-info text-dark'
                                : rfq.status === 'under_review'
                                ? 'bg-warning text-dark'
                                : rfq.status === 'quoted'
                                ? 'bg-success'
                                : 'bg-secondary'
                            }`}
                          >
                            {rfq.status.replace('_', ' ')}
                          </span>
                        </td>
                        <td className="text-end">
                          <button
                            onClick={() => openRfqDetails(rfq.id)}
                            className="btn btn-outline-secondary btn-sm"
                          >
                            View Specs
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: COMPANY PROFILE & SETTINGS (SLICE S02) */}
      {activeTab === 'profile' && (
        <div className="row g-4">
          <div className="col-12 col-lg-6">
            <div className="card shadow-sm border-0 rounded-3 h-100">
              <div className="card-header bg-white border-bottom py-3 d-flex justify-content-between align-items-center">
                <h5 className="card-title h6 mb-0 fw-bold">Business Profile Details</h5>
                {!isEditing && (
                  <button
                    onClick={() => {
                      setEditData({
                        company_name: profile?.company_name || '',
                        contact_person: profile?.contact_person || '',
                        phone: profile?.phone || '',
                        gstin: profile?.gstin || '',
                        address: profile?.address || '',
                      });
                      setIsEditing(true);
                    }}
                    className="btn btn-outline-primary btn-sm"
                  >
                    Edit Profile
                  </button>
                )}
              </div>

              <div className="card-body">
                {isEditing ? (
                  <form onSubmit={handleSaveProfile}>
                    <div className="mb-2">
                      <label className="form-label small fw-bold mb-1">Company Name</label>
                      <input
                        name="company_name"
                        type="text"
                        className="form-control form-control-sm"
                        value={editData.company_name}
                        onChange={handleProfileInputChange}
                        required
                      />
                    </div>

                    <div className="mb-2">
                      <label className="form-label small fw-bold mb-1">Contact Person</label>
                      <input
                        name="contact_person"
                        type="text"
                        className="form-control form-control-sm"
                        value={editData.contact_person}
                        onChange={handleProfileInputChange}
                        required
                      />
                    </div>

                    <div className="mb-2">
                      <label className="form-label small fw-bold mb-1">Phone Number</label>
                      <input
                        name="phone"
                        type="tel"
                        className="form-control form-control-sm"
                        value={editData.phone}
                        onChange={handleProfileInputChange}
                        required
                      />
                    </div>

                    <div className="mb-2">
                      <label className="form-label small fw-bold mb-1">GSTIN Number</label>
                      <input
                        name="gstin"
                        type="text"
                        className="form-control form-control-sm text-uppercase"
                        value={editData.gstin}
                        onChange={handleProfileInputChange}
                      />
                    </div>

                    <div className="mb-3">
                      <label className="form-label small fw-bold mb-1">Plant / Delivery Address</label>
                      <textarea
                        name="address"
                        rows="2"
                        className="form-control form-control-sm"
                        value={editData.address}
                        onChange={handleProfileInputChange}
                      ></textarea>
                    </div>

                    <div className="d-flex gap-2">
                      <button
                        type="submit"
                        className="btn btn-primary btn-sm fw-bold"
                        disabled={saveLoading}
                      >
                        {saveLoading ? 'Saving…' : 'Save Changes'}
                      </button>
                      <button
                        type="button"
                        className="btn btn-outline-secondary btn-sm"
                        onClick={() => setIsEditing(false)}
                        disabled={saveLoading}
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                ) : (
                  <div>
                    <p className="mb-1 text-secondary small">Company Name</p>
                    <h6 className="fw-bold mb-3">{profile?.company_name || 'Individual Customer'}</h6>

                    <p className="mb-1 text-secondary small">Contact Person</p>
                    <p className="mb-3">{profile?.contact_person || user?.email}</p>

                    <p className="mb-1 text-secondary small">Phone Number</p>
                    <p className="mb-3">{profile?.phone || 'Not provided'}</p>

                    <p className="mb-1 text-secondary small">GSTIN Registration</p>
                    <p className="mb-3">
                      <span className="badge bg-light text-dark border">
                        {profile?.gstin || 'Unregistered / Inter-state'}
                      </span>
                    </p>

                    <p className="mb-1 text-secondary small">Manufacturing Plant / Billing Address</p>
                    <p className="small text-muted mb-4">{profile?.address || 'Ahmedabad, Gujarat'}</p>

                    <div className="border-top pt-3">
                      <button
                        onClick={() => setIsPasswordModalOpen(true)}
                        className="btn btn-outline-secondary btn-sm w-100"
                      >
                        Change Account Password
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: SUPPORT & INQUIRIES WORKSPACE (SLICE S14) */}
      {activeTab === 'support' && (
        <div>
          <div className="card shadow-sm border-0 rounded-3 mb-4">
            <div className="card-header bg-white border-bottom py-3 d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
              <div>
                <h5 className="card-title h6 mb-1 fw-bold">Support Inquiries & Complaints (Slice S14)</h5>
                <p className="text-muted small mb-0">
                  Direct correspondence with KPC Management for technical pattern requirements, order complaints, and manufacturing queries.
                </p>
              </div>
              <button
                onClick={() => {
                  setTicketForm({ ticket_type: 'inquiry', subject: '', message: '', order_id: '', rfq_id: '' });
                  setTicketFiles([]);
                  setTicketFileError('');
                  fetchCustomerContext();
                  setIsTicketModalOpen(true);
                }}
                className="btn btn-primary btn-sm fw-bold d-flex align-items-center gap-2"
              >
                <span>➕</span> Raise Inquiry / Complaint
              </button>
            </div>

            {/* Filter Toolbar */}
            <div className="card-body bg-light border-bottom py-2">
              <div className="row g-2 align-items-center">
                <div className="col-auto">
                  <span className="small text-secondary fw-bold">Status:</span>
                </div>
                <div className="col-auto d-flex gap-1">
                  {['all', 'open', 'in_progress', 'resolved', 'closed'].map((st) => (
                    <button
                      key={st}
                      type="button"
                      className={`btn btn-sm ${ticketStatusFilter === st ? 'btn-primary' : 'btn-outline-secondary bg-white'}`}
                      style={{ fontSize: '0.8rem', padding: '0.2rem 0.55rem' }}
                      onClick={() => setTicketStatusFilter(st)}
                    >
                      {st === 'all' ? 'All' : st.replace('_', ' ').toUpperCase()}
                    </button>
                  ))}
                </div>

                <div className="col-auto ms-auto d-flex align-items-center gap-2">
                  <span className="small text-secondary fw-bold">Type:</span>
                  <select
                    className="form-select form-select-sm"
                    style={{ width: '160px', fontSize: '0.82rem' }}
                    value={ticketTypeFilter}
                    onChange={(e) => setTicketTypeFilter(e.target.value)}
                  >
                    <option value="all">All Types</option>
                    <option value="inquiry">Inquiry</option>
                    <option value="complaint">Complaint</option>
                    <option value="order_issue">Order Issue</option>
                    <option value="technical_support">Technical Support</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Ticket List */}
            <div className="card-body p-0">
              {loadingTickets ? (
                <div className="p-4 text-center text-muted">
                  <div className="spinner-border spinner-border-sm text-primary me-2"></div>
                  Loading support tickets...
                </div>
              ) : supportTickets.filter((t) => {
                  if (ticketStatusFilter !== 'all' && t.status !== ticketStatusFilter) return false;
                  if (ticketTypeFilter !== 'all' && t.ticket_type !== ticketTypeFilter) return false;
                  return true;
                }).length === 0 ? (
                <div className="p-5 text-center">
                  <div className="display-6 text-muted mb-3">💬</div>
                  <h6 className="fw-bold text-dark">No support tickets found</h6>
                  <p className="text-muted small mb-3">
                    Have a technical question about your casting patterns or need help with an order?
                  </p>
                  <button
                    onClick={() => {
                      fetchCustomerContext();
                      setIsTicketModalOpen(true);
                    }}
                    className="btn btn-outline-primary btn-sm"
                  >
                    Raise Your First Ticket
                  </button>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover align-middle mb-0">
                    <thead className="table-light small text-uppercase">
                      <tr>
                        <th className="ps-3">Ticket #</th>
                        <th>Type</th>
                        <th>Subject</th>
                        <th>Associated Ref</th>
                        <th>Status</th>
                        <th>Messages</th>
                        <th>Last Activity</th>
                        <th className="text-end pe-3">Action</th>
                      </tr>
                    </thead>
                    <tbody className="small">
                      {supportTickets
                        .filter((t) => {
                          if (ticketStatusFilter !== 'all' && t.status !== ticketStatusFilter) return false;
                          if (ticketTypeFilter !== 'all' && t.ticket_type !== ticketTypeFilter) return false;
                          return true;
                        })
                        .map((t) => (
                          <tr key={t.id}>
                            <td className="ps-3 fw-bold text-primary font-monospace">{t.ticket_number}</td>
                            <td>
                              <span
                                className={`badge ${
                                  t.ticket_type === 'complaint'
                                    ? 'bg-danger'
                                    : t.ticket_type === 'order_issue'
                                    ? 'bg-warning text-dark'
                                    : t.ticket_type === 'technical_support'
                                    ? 'bg-primary'
                                    : 'bg-info text-dark'
                                }`}
                              >
                                {t.ticket_type.replace('_', ' ').toUpperCase()}
                              </span>
                            </td>
                            <td>
                              <span className="fw-bold text-dark">{t.subject}</span>
                            </td>
                            <td>
                              {t.order_number ? (
                                <span className="badge bg-secondary font-monospace">ORD: {t.order_number}</span>
                              ) : t.rfq_number ? (
                                <span className="badge bg-light text-dark border font-monospace">RFQ: {t.rfq_number}</span>
                              ) : (
                                <span className="text-muted small">—</span>
                              )}
                            </td>
                            <td>
                              <span
                                className={`badge ${
                                  t.status === 'open'
                                    ? 'bg-primary'
                                    : t.status === 'in_progress'
                                    ? 'bg-warning text-dark'
                                    : t.status === 'resolved'
                                    ? 'bg-success'
                                    : 'bg-secondary'
                                }`}
                              >
                                {t.status.replace('_', ' ').toUpperCase()}
                              </span>
                            </td>
                            <td>
                              <span className="badge bg-light text-dark border">
                                💬 {t.message_count}
                              </span>
                            </td>
                            <td className="text-muted">
                              {new Date(t.updated_at).toLocaleDateString()}
                            </td>
                            <td className="text-end pe-3">
                              <button
                                onClick={() => handleOpenTicket(t.id)}
                                className="btn btn-outline-primary btn-sm fw-bold"
                              >
                                Open Conversation
                              </button>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 3-STEP RFQ SUBMISSION MODAL (SLICE S05) */}
      {isRfqModalOpen && (
        <div
          className="modal show d-block"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.65)' }}
          tabIndex="-1"
        >
          <div className="modal-dialog modal-dialog-centered modal-lg">
            <div className="modal-content border-0 shadow-lg rounded-4 p-3 p-md-4">
              <div className="modal-header border-0 pb-2">
                <div>
                  <h5 className="modal-title fw-bold">Request For Quotation (RFQ)</h5>
                  <p className="text-muted small mb-0">Step {rfqStep} of 3: Pattern Engineering Requirements</p>
                </div>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setIsRfqModalOpen(false)}
                  disabled={submittingRfq}
                ></button>
              </div>

              {/* Step indicator bar */}
              <div className="px-3 mb-4">
                <div className="progress" style={{ height: '6px' }}>
                  <div
                    className="progress-bar bg-primary"
                    style={{ width: `${(rfqStep / 3) * 100}%` }}
                  ></div>
                </div>
                <div className="d-flex justify-content-between mt-2 small text-muted">
                  <span className={rfqStep >= 1 ? 'fw-bold text-primary' : ''}>1. Pattern Info</span>
                  <span className={rfqStep >= 2 ? 'fw-bold text-primary' : ''}>2. Technical Specs</span>
                  <span className={rfqStep >= 3 ? 'fw-bold text-primary' : ''}>3. Review & Submit</span>
                </div>
              </div>

              <div className="modal-body pt-0">
                <form onSubmit={handleRfqSubmit}>
                  {/* STEP 1: PATTERN INFO */}
                  {rfqStep === 1 && (
                    <div className="row g-3">
                      <div className="col-12">
                        <label className="form-label small fw-bold">Requirement Type</label>
                        <div className="d-flex gap-4">
                          <div className="form-check">
                            <input
                              className="form-check-input"
                              type="radio"
                              name="rfq_type"
                              id="rfq_type_custom"
                              value="custom"
                              checked={rfqForm.rfq_type === 'custom'}
                              onChange={(e) =>
                                setRfqForm({ ...rfqForm, rfq_type: e.target.value, product_id: '' })
                              }
                            />
                            <label className="form-check-label" htmlFor="rfq_type_custom">
                              <strong>Custom Industrial Pattern</strong> (New fabrication)
                            </label>
                          </div>
                          <div className="form-check">
                            <input
                              className="form-check-input"
                              type="radio"
                              name="rfq_type"
                              id="rfq_type_standard"
                              value="standard"
                              checked={rfqForm.rfq_type === 'standard'}
                              onChange={(e) =>
                                setRfqForm({ ...rfqForm, rfq_type: e.target.value })
                              }
                            />
                            <label className="form-check-label" htmlFor="rfq_type_standard">
                              <strong>Standard Catalogue Pattern</strong> (KPC Portfolio)
                            </label>
                          </div>
                        </div>
                      </div>

                      {rfqForm.rfq_type === 'standard' && (
                        <div className="col-12">
                          <label className="form-label small fw-bold">Select Catalogue Product *</label>
                          <select
                            className="form-select"
                            value={rfqForm.product_id}
                            onChange={(e) => {
                              const prodId = e.target.value;
                              const selectedProd = catalogueProducts.find((p) => p.id === Number(prodId));
                              setRfqForm({
                                ...rfqForm,
                                product_id: prodId,
                                title: selectedProd ? selectedProd.name : rfqForm.title,
                                material: selectedProd?.material_type || rfqForm.material,
                              });
                            }}
                            required
                          >
                            <option value="">-- Choose Catalogue Pattern --</option>
                            {catalogueProducts.map((p) => (
                              <option key={p.id} value={p.id}>
                                {p.name} ({p.material_type || 'Custom Material'})
                              </option>
                            ))}
                          </select>
                        </div>
                      )}

                      <div className="col-12 col-md-8">
                        <label className="form-label small fw-bold">Pattern / Part Title *</label>
                        <input
                          type="text"
                          className="form-control"
                          placeholder="e.g. 500mm Impeller Casting Pattern"
                          value={rfqForm.title}
                          onChange={(e) => setRfqForm({ ...rfqForm, title: e.target.value })}
                          required
                        />
                      </div>

                      <div className="col-12 col-md-4">
                        <label className="form-label small fw-bold">Quantity (Pcs) *</label>
                        <input
                          type="number"
                          className="form-control"
                          min="1"
                          value={rfqForm.quantity}
                          onChange={(e) => setRfqForm({ ...rfqForm, quantity: e.target.value })}
                          required
                        />
                      </div>

                      <div className="col-12 col-md-6">
                        <label className="form-label small fw-bold">Material Specification *</label>
                        <select
                          className="form-select"
                          value={rfqForm.material}
                          onChange={(e) => setRfqForm({ ...rfqForm, material: e.target.value })}
                        >
                          <option value="Teak Wood">Teak Wood (Seasoned)</option>
                          <option value="Mahogany Wood">Mahogany Wood (Hardwood)</option>
                          <option value="Aluminum Alloy 7075">Aluminum Alloy 7075 (CNC Machined)</option>
                          <option value="Cast Iron Grade 25">Cast Iron Grade 25 (Wear Resistant)</option>
                          <option value="Tool Steel">High-Carbon Tool Steel</option>
                          <option value="Polyurethane / Epoxy">Polyurethane / Resin Board</option>
                        </select>
                      </div>

                      <div className="col-12 col-md-6">
                        <label className="form-label small fw-bold">Target Delivery Date</label>
                        <input
                          type="date"
                          className="form-control"
                          value={rfqForm.target_delivery_date}
                          onChange={(e) =>
                            setRfqForm({ ...rfqForm, target_delivery_date: e.target.value })
                          }
                        />
                      </div>

                      <div className="col-12">
                        <label className="form-label small fw-bold">Part Description & Usage</label>
                        <textarea
                          rows="2"
                          className="form-control"
                          placeholder="Describe casting application, foundry method (sand / die / investment), etc."
                          value={rfqForm.description}
                          onChange={(e) =>
                            setRfqForm({ ...rfqForm, description: e.target.value })
                          }
                        ></textarea>
                      </div>

                      <div className="col-12 text-end mt-4">
                        <button
                          type="button"
                          className="btn btn-primary"
                          onClick={() => {
                            if (!rfqForm.title.trim()) {
                              alert('Please enter a pattern title.');
                              return;
                            }
                            if (rfqForm.rfq_type === 'standard' && !rfqForm.product_id) {
                              alert('Please select a catalogue product.');
                              return;
                            }
                            setRfqStep(2);
                          }}
                        >
                          Next: Technical Specifications →
                        </button>
                      </div>
                    </div>
                  )}

                  {/* STEP 2: TECHNICAL SPECS & FILES */}
                  {rfqStep === 2 && (
                    <div className="row g-3">
                      <div className="col-12 col-md-6">
                        <label className="form-label small fw-bold">Dimensions (Length x Width x Height)</label>
                        <input
                          type="text"
                          className="form-control"
                          placeholder="e.g. 600mm x 400mm x 250mm"
                          value={rfqForm.dimensions}
                          onChange={(e) =>
                            setRfqForm({ ...rfqForm, dimensions: e.target.value })
                          }
                        />
                      </div>

                      <div className="col-12 col-md-6">
                        <label className="form-label small fw-bold">Engineering Allowances & Tolerances</label>
                        <input
                          type="text"
                          className="form-control"
                          placeholder="e.g. ±0.1mm tolerance, 1.5% shrinkage"
                          value={rfqForm.specifications}
                          onChange={(e) =>
                            setRfqForm({ ...rfqForm, specifications: e.target.value })
                          }
                        />
                      </div>

                      <div className="col-12">
                        <label className="form-label small fw-bold">Special Tooling Notes</label>
                        <textarea
                          rows="2"
                          className="form-control"
                          placeholder="Core box requirements, loose pieces, draft angles, or finishing coat instructions."
                          value={rfqForm.notes}
                          onChange={(e) => setRfqForm({ ...rfqForm, notes: e.target.value })}
                        ></textarea>
                      </div>

                      {/* S06 CAD Drawings & Blueprint Upload */}
                      <div className="col-12">
                        <label className="form-label small fw-bold">
                          CAD Drawings & Technical Blueprints (Optional, Max 2 Files, 20 MB each)
                        </label>
                        <div className="card p-3 border-2 border-dashed bg-light text-center">
                          <input
                            type="file"
                            id="rfqFileInput"
                            className="d-none"
                            multiple
                            accept=".pdf,.png,.jpg,.jpeg,.webp,.step,.stp,.iges,.igs,.stl,.dwg,.dxf"
                            onChange={handleFileSelect}
                            disabled={selectedFiles.length >= 2}
                          />
                          <div>
                            <label
                              htmlFor="rfqFileInput"
                              className={`btn btn-outline-primary btn-sm mb-2 ${selectedFiles.length >= 2 ? 'disabled' : ''}`}
                              style={{ cursor: selectedFiles.length >= 2 ? 'not-allowed' : 'pointer' }}
                            >
                              📁 Choose Technical Drawings / CAD Files
                            </label>
                            <p className="small text-muted mb-0">
                              Allowed formats: <strong>PDF, PNG, JPG, WEBP, STEP (.step/.stp), IGES (.iges/.igs), STL, DWG, DXF</strong>
                            </p>
                          </div>
                        </div>

                        {fileUploadError && (
                          <div className="alert alert-danger small py-2 mt-2 mb-0">
                            {fileUploadError}
                          </div>
                        )}

                        {selectedFiles.length > 0 && (
                          <div className="mt-3">
                            <h6 className="small fw-bold text-dark mb-2">
                              Selected Attachments ({selectedFiles.length}/2):
                            </h6>
                            <div className="list-group">
                              {selectedFiles.map((file, idx) => (
                                <div
                                  key={idx}
                                  className="list-group-item d-flex justify-content-between align-items-center py-2 px-3 bg-white rounded border mb-2"
                                >
                                  <div>
                                    <span className="badge bg-secondary me-2">
                                      {getFileExtension(file.name)}
                                    </span>
                                    <span className="fw-semibold small">{file.name}</span>
                                    <span className="text-muted small ms-2">
                                      ({formatFileSize(file.size)})
                                    </span>
                                  </div>
                                  <button
                                    type="button"
                                    className="btn btn-outline-danger btn-sm py-0 px-2"
                                    onClick={() => handleRemoveSelectedFile(idx)}
                                  >
                                    ✕ Remove
                                  </button>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      <div className="col-12 d-flex justify-content-between mt-4">
                        <button
                          type="button"
                          className="btn btn-outline-secondary"
                          onClick={() => setRfqStep(1)}
                        >
                          ← Back to Pattern Info
                        </button>
                        <button
                          type="button"
                          className="btn btn-primary"
                          onClick={() => setRfqStep(3)}
                        >
                          Next: Review & Submit →
                        </button>
                      </div>
                    </div>
                  )}

                  {/* STEP 3: REVIEW & SUBMIT */}
                  {rfqStep === 3 && (
                    <div className="row g-3">
                      <div className="col-12">
                        <div className="alert alert-light border rounded-3 p-3 mb-3">
                          <h6 className="fw-bold text-dark mb-2">Requirement Summary</h6>
                          <div className="row g-2 small">
                            <div className="col-6"><strong>Pattern Title:</strong> {rfqForm.title}</div>
                            <div className="col-6"><strong>Type:</strong> <span className="text-uppercase badge bg-secondary">{rfqForm.rfq_type}</span></div>
                            <div className="col-6"><strong>Material:</strong> {rfqForm.material}</div>
                            <div className="col-6"><strong>Quantity:</strong> {rfqForm.quantity} pcs</div>
                            <div className="col-6"><strong>Dimensions:</strong> {rfqForm.dimensions || 'As per drawing'}</div>
                            <div className="col-6"><strong>Target Date:</strong> {rfqForm.target_delivery_date || 'Standard lead time'}</div>
                            {rfqForm.specifications && (
                              <div className="col-12"><strong>Specifications:</strong> {rfqForm.specifications}</div>
                            )}
                            <div className="col-12">
                              <strong>Attachments ({selectedFiles.length}/2):</strong>{' '}
                              {selectedFiles.length > 0 ? (
                                selectedFiles.map((f) => f.name).join(', ')
                              ) : (
                                <span className="text-muted">None attached</span>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="card border-0 bg-light p-3 rounded-3 mb-3">
                          <h6 className="fw-bold small mb-1">Company Contact Information (From Profile)</h6>
                          <p className="small text-muted mb-0">
                            <strong>{profile?.company_name || 'Individual Customer'}</strong> · Contact: {profile?.contact_person} · {profile?.phone}
                          </p>
                        </div>
                      </div>

                      <div className="col-12 d-flex justify-content-between mt-3">
                        <button
                          type="button"
                          className="btn btn-outline-secondary"
                          onClick={() => setRfqStep(2)}
                          disabled={submittingRfq}
                        >
                          ← Edit Technical Specs
                        </button>
                        <button
                          type="submit"
                          className="btn btn-primary btn-lg fw-bold"
                          disabled={submittingRfq}
                        >
                          {submittingRfq ? 'Submitting to KPC Engineering…' : 'Submit Official RFQ'}
                        </button>
                      </div>
                    </div>
                  )}
                </form>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: SUPPORT & INQUIRIES WORKSPACE (SLICE S14) */}
      {activeTab === 'support' && (
        <div>
          <div className="card shadow-sm border-0 rounded-3 mb-4">
            <div className="card-header bg-white border-bottom py-3 d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
              <div>
                <h5 className="card-title h6 mb-1 fw-bold">Support Inquiries & Complaints (Slice S14)</h5>
                <p className="text-muted small mb-0">
                  Direct correspondence with KPC Management for technical pattern requirements, order complaints, and manufacturing queries.
                </p>
              </div>
              <button
                onClick={() => {
                  setTicketForm({ ticket_type: 'inquiry', subject: '', message: '', order_id: '', rfq_id: '' });
                  setTicketFiles([]);
                  setTicketFileError('');
                  fetchCustomerContext();
                  setIsTicketModalOpen(true);
                }}
                className="btn btn-primary btn-sm fw-bold d-flex align-items-center gap-2"
              >
                <span>➕</span> Raise Inquiry / Complaint
              </button>
            </div>

            {/* Filter Toolbar */}
            <div className="card-body bg-light border-bottom py-2">
              <div className="row g-2 align-items-center">
                <div className="col-auto">
                  <span className="small text-secondary fw-bold">Status:</span>
                </div>
                <div className="col-auto d-flex gap-1">
                  {['all', 'open', 'in_progress', 'resolved', 'closed'].map((st) => (
                    <button
                      key={st}
                      type="button"
                      className={`btn btn-sm ${ticketStatusFilter === st ? 'btn-primary' : 'btn-outline-secondary bg-white'}`}
                      style={{ fontSize: '0.8rem', padding: '0.2rem 0.55rem' }}
                      onClick={() => setTicketStatusFilter(st)}
                    >
                      {st === 'all' ? 'All' : st.replace('_', ' ').toUpperCase()}
                    </button>
                  ))}
                </div>

                <div className="col-auto ms-auto d-flex align-items-center gap-2">
                  <span className="small text-secondary fw-bold">Type:</span>
                  <select
                    className="form-select form-select-sm"
                    style={{ width: '160px', fontSize: '0.82rem' }}
                    value={ticketTypeFilter}
                    onChange={(e) => setTicketTypeFilter(e.target.value)}
                  >
                    <option value="all">All Types</option>
                    <option value="inquiry">Inquiry</option>
                    <option value="complaint">Complaint</option>
                    <option value="order_issue">Order Issue</option>
                    <option value="technical_support">Technical Support</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Ticket List */}
            <div className="card-body p-0">
              {loadingTickets ? (
                <div className="p-4 text-center text-muted">
                  <div className="spinner-border spinner-border-sm text-primary me-2"></div>
                  Loading support tickets...
                </div>
              ) : supportTickets.filter((t) => {
                  if (ticketStatusFilter !== 'all' && t.status !== ticketStatusFilter) return false;
                  if (ticketTypeFilter !== 'all' && t.ticket_type !== ticketTypeFilter) return false;
                  return true;
                }).length === 0 ? (
                <div className="p-5 text-center">
                  <div className="display-6 text-muted mb-3">💬</div>
                  <h6 className="fw-bold text-dark">No support tickets found</h6>
                  <p className="text-muted small mb-3">
                    Have a technical question about your casting patterns or need help with an order?
                  </p>
                  <button
                    onClick={() => {
                      fetchCustomerContext();
                      setIsTicketModalOpen(true);
                    }}
                    className="btn btn-outline-primary btn-sm"
                  >
                    Raise Your First Ticket
                  </button>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover align-middle mb-0">
                    <thead className="table-light small text-uppercase">
                      <tr>
                        <th className="ps-3">Ticket #</th>
                        <th>Type</th>
                        <th>Subject</th>
                        <th>Associated Ref</th>
                        <th>Status</th>
                        <th>Messages</th>
                        <th>Last Activity</th>
                        <th className="text-end pe-3">Action</th>
                      </tr>
                    </thead>
                    <tbody className="small">
                      {supportTickets
                        .filter((t) => {
                          if (ticketStatusFilter !== 'all' && t.status !== ticketStatusFilter) return false;
                          if (ticketTypeFilter !== 'all' && t.ticket_type !== ticketTypeFilter) return false;
                          return true;
                        })
                        .map((t) => (
                          <tr key={t.id}>
                            <td className="ps-3 fw-bold text-primary font-monospace">{t.ticket_number}</td>
                            <td>
                              <span
                                className={`badge ${
                                  t.ticket_type === 'complaint'
                                    ? 'bg-danger'
                                    : t.ticket_type === 'order_issue'
                                    ? 'bg-warning text-dark'
                                    : t.ticket_type === 'technical_support'
                                    ? 'bg-primary'
                                    : 'bg-info text-dark'
                                }`}
                              >
                                {t.ticket_type.replace('_', ' ').toUpperCase()}
                              </span>
                            </td>
                            <td>
                              <span className="fw-bold text-dark">{t.subject}</span>
                            </td>
                            <td>
                              {t.order_number ? (
                                <span className="badge bg-secondary font-monospace">ORD: {t.order_number}</span>
                              ) : t.rfq_number ? (
                                <span className="badge bg-light text-dark border font-monospace">RFQ: {t.rfq_number}</span>
                              ) : (
                                <span className="text-muted small">—</span>
                              )}
                            </td>
                            <td>
                              <span
                                className={`badge ${
                                  t.status === 'open'
                                    ? 'bg-primary'
                                    : t.status === 'in_progress'
                                    ? 'bg-warning text-dark'
                                    : t.status === 'resolved'
                                    ? 'bg-success'
                                    : 'bg-secondary'
                                }`}
                              >
                                {t.status.replace('_', ' ').toUpperCase()}
                              </span>
                            </td>
                            <td>
                              <span className="badge bg-light text-dark border">
                                💬 {t.message_count}
                              </span>
                            </td>
                            <td className="text-muted">
                              {new Date(t.updated_at).toLocaleDateString()}
                            </td>
                            <td className="text-end pe-3">
                              <button
                                onClick={() => handleOpenTicket(t.id)}
                                className="btn btn-outline-primary btn-sm fw-bold"
                              >
                                Open Conversation
                              </button>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* RFQ DETAIL MODAL */}
      {selectedRfqDetail && (
        <div
          className="modal show d-block"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.65)' }}
          tabIndex="-1"
        >
          <div className="modal-dialog modal-dialog-centered modal-lg">
            <div className="modal-content border-0 shadow-lg rounded-4 p-3 p-md-4">
              <div className="modal-header border-0 pb-2">
                <div>
                  <span className="badge bg-primary text-uppercase me-2">{selectedRfqDetail.rfq_type}</span>
                  <span className="badge bg-warning text-dark text-uppercase">{selectedRfqDetail.status.replace('_', ' ')}</span>
                  <h4 className="modal-title fw-bold mt-2">{selectedRfqDetail.title}</h4>
                  <p className="text-muted small mb-0">Reference: {selectedRfqDetail.rfq_number}</p>
                </div>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setSelectedRfqDetail(null)}
                ></button>
              </div>

              <div className="modal-body">
                <div className="row g-3 small">
                  <div className="col-md-6">
                    <p className="mb-1 text-muted">Material</p>
                    <h6 className="fw-bold">{selectedRfqDetail.material}</h6>
                  </div>
                  <div className="col-md-6">
                    <p className="mb-1 text-muted">Quantity</p>
                    <h6 className="fw-bold">{selectedRfqDetail.quantity} pieces</h6>
                  </div>
                  <div className="col-md-6">
                    <p className="mb-1 text-muted">Dimensions</p>
                    <p className="fw-semibold">{selectedRfqDetail.dimensions || 'As per CAD drawing'}</p>
                  </div>
                  <div className="col-md-6">
                    <p className="mb-1 text-muted">Target Delivery Date</p>
                    <p className="fw-semibold">{selectedRfqDetail.target_delivery_date || 'Standard delivery'}</p>
                  </div>
                  {selectedRfqDetail.specifications && (
                    <div className="col-12">
                      <p className="mb-1 text-muted">Technical Tolerances / Allowances</p>
                      <p className="p-2 bg-light rounded">{selectedRfqDetail.specifications}</p>
                    </div>
                  )}
                  {selectedRfqDetail.description && (
                    <div className="col-12">
                      <p className="mb-1 text-muted">Description & Casting Process</p>
                      <p className="p-2 bg-light rounded">{selectedRfqDetail.description}</p>
                    </div>
                  )}
                  {selectedRfqDetail.notes && (
                    <div className="col-12">
                      <p className="mb-1 text-muted">Tooling Notes</p>
                      <p className="p-2 bg-light rounded">{selectedRfqDetail.notes}</p>
                    </div>
                  )}

                  {/* S06 Attached Files List */}
                  <div className="col-12 mt-3 pt-3 border-top">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                      <h6 className="fw-bold small text-dark mb-0">
                        Attached Drawings & CAD Models ({selectedRfqDetail.files?.length || 0}/2)
                      </h6>
                      {selectedRfqDetail.status === 'submitted' &&
                        (!selectedRfqDetail.files || selectedRfqDetail.files.length < 2) && (
                          <label
                            className="btn btn-outline-primary btn-sm py-1 px-2 mb-0"
                            style={{ cursor: 'pointer' }}
                          >
                            + Attach Drawing
                            <input
                              type="file"
                              className="d-none"
                              accept=".pdf,.png,.jpg,.jpeg,.webp,.step,.stp,.iges,.igs,.stl,.dwg,.dxf"
                              onChange={(e) =>
                                handleUploadExtraFile(selectedRfqDetail.id, e.target.files[0])
                              }
                              disabled={isAttachingExtraFile}
                            />
                          </label>
                        )}
                    </div>

                    {isAttachingExtraFile && (
                      <p className="small text-primary mb-2">Uploading attachment…</p>
                    )}
                    {extraFileError && (
                      <div className="alert alert-danger small py-1 px-2 mb-2">
                        {extraFileError}
                      </div>
                    )}

                    {!selectedRfqDetail.files || selectedRfqDetail.files.length === 0 ? (
                      <p className="small text-muted mb-0">
                        No blueprints or CAD files attached to this RFQ.
                      </p>
                    ) : (
                      <div className="list-group">
                        {selectedRfqDetail.files.map((file) => (
                          <div
                            key={file.id}
                            className="list-group-item d-flex justify-content-between align-items-center py-2 px-3 bg-light rounded border mb-2"
                          >
                            <div>
                              <span className="badge bg-primary text-uppercase me-2">
                                {getFileExtension(file.file_name)}
                              </span>
                              <span className="fw-semibold small">{file.file_name}</span>
                              <span className="text-muted small ms-2">
                                ({formatFileSize(file.file_size_bytes)})
                              </span>
                            </div>
                            <div className="d-flex gap-2">
                              {file.can_preview && (
                                <button
                                  type="button"
                                  className="btn btn-sm btn-outline-primary py-0 px-2"
                                  onClick={() =>
                                    setPreviewFile({
                                      rfqId: selectedRfqDetail.id,
                                      fileId: file.id,
                                      fileName: file.file_name,
                                      contentType: file.content_type,
                                    })
                                  }
                                >
                                  👁 Preview
                                </button>
                              )}
                              <a
                                href={`${API_BASE}/rfqs/${selectedRfqDetail.id}/files/${file.id}?disposition=attachment`}
                                className="btn btn-sm btn-outline-secondary py-0 px-2"
                                download
                              >
                                ⬇ Download
                              </a>
                              {selectedRfqDetail.status === 'submitted' && (
                                <button
                                  type="button"
                                  className="btn btn-sm btn-outline-danger py-0 px-2"
                                  onClick={() =>
                                    handleDeleteAttachedFile(selectedRfqDetail.id, file.id)
                                  }
                                >
                                  🗑
                                </button>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <div className="modal-footer border-0">
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setSelectedRfqDetail(null)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: SUPPORT & INQUIRIES WORKSPACE (SLICE S14) */}
      {activeTab === 'support' && (
        <div>
          <div className="card shadow-sm border-0 rounded-3 mb-4">
            <div className="card-header bg-white border-bottom py-3 d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
              <div>
                <h5 className="card-title h6 mb-1 fw-bold">Support Inquiries & Complaints (Slice S14)</h5>
                <p className="text-muted small mb-0">
                  Direct correspondence with KPC Management for technical pattern requirements, order complaints, and manufacturing queries.
                </p>
              </div>
              <button
                onClick={() => {
                  setTicketForm({ ticket_type: 'inquiry', subject: '', message: '', order_id: '', rfq_id: '' });
                  setTicketFiles([]);
                  setTicketFileError('');
                  fetchCustomerContext();
                  setIsTicketModalOpen(true);
                }}
                className="btn btn-primary btn-sm fw-bold d-flex align-items-center gap-2"
              >
                <span>➕</span> Raise Inquiry / Complaint
              </button>
            </div>

            {/* Filter Toolbar */}
            <div className="card-body bg-light border-bottom py-2">
              <div className="row g-2 align-items-center">
                <div className="col-auto">
                  <span className="small text-secondary fw-bold">Status:</span>
                </div>
                <div className="col-auto d-flex gap-1">
                  {['all', 'open', 'in_progress', 'resolved', 'closed'].map((st) => (
                    <button
                      key={st}
                      type="button"
                      className={`btn btn-sm ${ticketStatusFilter === st ? 'btn-primary' : 'btn-outline-secondary bg-white'}`}
                      style={{ fontSize: '0.8rem', padding: '0.2rem 0.55rem' }}
                      onClick={() => setTicketStatusFilter(st)}
                    >
                      {st === 'all' ? 'All' : st.replace('_', ' ').toUpperCase()}
                    </button>
                  ))}
                </div>

                <div className="col-auto ms-auto d-flex align-items-center gap-2">
                  <span className="small text-secondary fw-bold">Type:</span>
                  <select
                    className="form-select form-select-sm"
                    style={{ width: '160px', fontSize: '0.82rem' }}
                    value={ticketTypeFilter}
                    onChange={(e) => setTicketTypeFilter(e.target.value)}
                  >
                    <option value="all">All Types</option>
                    <option value="inquiry">Inquiry</option>
                    <option value="complaint">Complaint</option>
                    <option value="order_issue">Order Issue</option>
                    <option value="technical_support">Technical Support</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Ticket List */}
            <div className="card-body p-0">
              {loadingTickets ? (
                <div className="p-4 text-center text-muted">
                  <div className="spinner-border spinner-border-sm text-primary me-2"></div>
                  Loading support tickets...
                </div>
              ) : supportTickets.filter((t) => {
                  if (ticketStatusFilter !== 'all' && t.status !== ticketStatusFilter) return false;
                  if (ticketTypeFilter !== 'all' && t.ticket_type !== ticketTypeFilter) return false;
                  return true;
                }).length === 0 ? (
                <div className="p-5 text-center">
                  <div className="display-6 text-muted mb-3">💬</div>
                  <h6 className="fw-bold text-dark">No support tickets found</h6>
                  <p className="text-muted small mb-3">
                    Have a technical question about your casting patterns or need help with an order?
                  </p>
                  <button
                    onClick={() => {
                      fetchCustomerContext();
                      setIsTicketModalOpen(true);
                    }}
                    className="btn btn-outline-primary btn-sm"
                  >
                    Raise Your First Ticket
                  </button>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover align-middle mb-0">
                    <thead className="table-light small text-uppercase">
                      <tr>
                        <th className="ps-3">Ticket #</th>
                        <th>Type</th>
                        <th>Subject</th>
                        <th>Associated Ref</th>
                        <th>Status</th>
                        <th>Messages</th>
                        <th>Last Activity</th>
                        <th className="text-end pe-3">Action</th>
                      </tr>
                    </thead>
                    <tbody className="small">
                      {supportTickets
                        .filter((t) => {
                          if (ticketStatusFilter !== 'all' && t.status !== ticketStatusFilter) return false;
                          if (ticketTypeFilter !== 'all' && t.ticket_type !== ticketTypeFilter) return false;
                          return true;
                        })
                        .map((t) => (
                          <tr key={t.id}>
                            <td className="ps-3 fw-bold text-primary font-monospace">{t.ticket_number}</td>
                            <td>
                              <span
                                className={`badge ${
                                  t.ticket_type === 'complaint'
                                    ? 'bg-danger'
                                    : t.ticket_type === 'order_issue'
                                    ? 'bg-warning text-dark'
                                    : t.ticket_type === 'technical_support'
                                    ? 'bg-primary'
                                    : 'bg-info text-dark'
                                }`}
                              >
                                {t.ticket_type.replace('_', ' ').toUpperCase()}
                              </span>
                            </td>
                            <td>
                              <span className="fw-bold text-dark">{t.subject}</span>
                            </td>
                            <td>
                              {t.order_number ? (
                                <span className="badge bg-secondary font-monospace">ORD: {t.order_number}</span>
                              ) : t.rfq_number ? (
                                <span className="badge bg-light text-dark border font-monospace">RFQ: {t.rfq_number}</span>
                              ) : (
                                <span className="text-muted small">—</span>
                              )}
                            </td>
                            <td>
                              <span
                                className={`badge ${
                                  t.status === 'open'
                                    ? 'bg-primary'
                                    : t.status === 'in_progress'
                                    ? 'bg-warning text-dark'
                                    : t.status === 'resolved'
                                    ? 'bg-success'
                                    : 'bg-secondary'
                                }`}
                              >
                                {t.status.replace('_', ' ').toUpperCase()}
                              </span>
                            </td>
                            <td>
                              <span className="badge bg-light text-dark border">
                                💬 {t.message_count}
                              </span>
                            </td>
                            <td className="text-muted">
                              {new Date(t.updated_at).toLocaleDateString()}
                            </td>
                            <td className="text-end pe-3">
                              <button
                                onClick={() => handleOpenTicket(t.id)}
                                className="btn btn-outline-primary btn-sm fw-bold"
                              >
                                Open Conversation
                              </button>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* IN-BROWSER FILE PREVIEW MODAL (SLICE S06) */}
      {previewFile && (
        <div
          className="modal show d-block"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.75)', zIndex: 1060 }}
          tabIndex="-1"
        >
          <div className="modal-dialog modal-dialog-centered modal-xl">
            <div className="modal-content border-0 shadow-lg rounded-4 p-3">
              <div className="modal-header border-bottom pb-2">
                <div>
                  <span className="badge bg-primary text-uppercase me-2">
                    {getFileExtension(previewFile.fileName)}
                  </span>
                  <h5 className="modal-title fw-bold d-inline align-middle">
                    {previewFile.fileName}
                  </h5>
                </div>
                <div className="d-flex gap-2">
                  <a
                    href={
                      previewFile.ticketId
                        ? `${API_BASE}/support/tickets/${previewFile.ticketId}/files/${previewFile.fileId}?disposition=attachment`
                        : `${API_BASE}/rfqs/${previewFile.rfqId}/files/${previewFile.fileId}?disposition=attachment`
                    }
                    className="btn btn-outline-secondary btn-sm"
                    download
                  >
                    ⬇ Download
                  </a>
                  <button
                    type="button"
                    className="btn-close"
                    onClick={() => setPreviewFile(null)}
                  ></button>
                </div>
              </div>
              <div
                className="modal-body p-2 text-center"
                style={{ minHeight: '500px', maxHeight: '80vh', overflowY: 'auto' }}
              >
                {previewFile.contentType === 'application/pdf' ? (
                  <iframe
                    src={
                      previewFile.ticketId
                        ? `${API_BASE}/support/tickets/${previewFile.ticketId}/files/${previewFile.fileId}?disposition=inline`
                        : `${API_BASE}/rfqs/${previewFile.rfqId}/files/${previewFile.fileId}?disposition=inline`
                    }
                    title={previewFile.fileName}
                    style={{
                      width: '100%',
                      height: '70vh',
                      border: 'none',
                      borderRadius: '8px',
                    }}
                  />
                ) : (
                  <img
                    src={
                      previewFile.ticketId
                        ? `${API_BASE}/support/tickets/${previewFile.ticketId}/files/${previewFile.fileId}?disposition=inline`
                        : `${API_BASE}/rfqs/${previewFile.rfqId}/files/${previewFile.fileId}?disposition=inline`
                    }
                    alt={previewFile.fileName}
                    className="img-fluid rounded shadow-sm"
                    style={{ maxHeight: '70vh', objectFit: 'contain' }}
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      )}


      {/* RAISE SUPPORT INQUIRY / COMPLAINT MODAL (SLICE S14) */}
      {isTicketModalOpen && (
        <div
          className="modal show d-block"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.65)' }}
          tabIndex="-1"
        >
          <div className="modal-dialog modal-dialog-centered modal-lg">
            <div className="modal-content border-0 shadow-lg rounded-4 p-3 p-md-4">
              <div className="modal-header border-0 pb-2">
                <div>
                  <h5 className="modal-title fw-bold">Raise Support Inquiry or Complaint</h5>
                  <p className="text-muted small mb-0">REQ-30 · Direct communication with KPC engineering & management</p>
                </div>
                <button
                  type="button"
                  className="btn-close"
                  onClick={() => setIsTicketModalOpen(false)}
                ></button>
              </div>

              {ticketFileError && (
                <div className="alert alert-danger small py-2">{ticketFileError}</div>
              )}

              <form onSubmit={handleCreateTicket}>
                <div className="modal-body py-2">
                  <div className="row g-3 mb-3">
                    <div className="col-12 col-md-6">
                      <label className="form-label small fw-bold">Ticket Classification *</label>
                      <select
                        className="form-select form-select-sm"
                        value={ticketForm.ticket_type}
                        onChange={(e) => setTicketForm({ ...ticketForm, ticket_type: e.target.value })}
                        required
                      >
                        <option value="inquiry">General Technical Inquiry</option>
                        <option value="complaint">Quality or Manufacturing Complaint</option>
                        <option value="order_issue">Order / Invoice Issue</option>
                        <option value="technical_support">CAD / Blueprint Technical Support</option>
                      </select>
                    </div>

                    <div className="col-12 col-md-6">
                      <label className="form-label small fw-bold">Link Related Order (Optional)</label>
                      <select
                        className="form-select form-select-sm"
                        value={ticketForm.order_id}
                        onChange={(e) => setTicketForm({ ...ticketForm, order_id: e.target.value })}
                      >
                        <option value="">-- No Related Order --</option>
                        {customerContext.orders.map((ord) => (
                          <option key={ord.id} value={ord.id}>
                            {ord.order_number} ({ord.status})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="row g-3 mb-3">
                    <div className="col-12 col-md-6">
                      <label className="form-label small fw-bold">Subject / Title *</label>
                      <input
                        type="text"
                        className="form-control form-control-sm"
                        placeholder="Brief summary of your query or issue..."
                        value={ticketForm.subject}
                        onChange={(e) => setTicketForm({ ...ticketForm, subject: e.target.value })}
                        required
                        minLength={3}
                        maxLength={255}
                      />
                    </div>

                    <div className="col-12 col-md-6">
                      <label className="form-label small fw-bold">Link Related RFQ (Optional)</label>
                      <select
                        className="form-select form-select-sm"
                        value={ticketForm.rfq_id}
                        onChange={(e) => setTicketForm({ ...ticketForm, rfq_id: e.target.value })}
                      >
                        <option value="">-- No Related RFQ --</option>
                        {customerContext.rfqs.map((rfq) => (
                          <option key={rfq.id} value={rfq.id}>
                            {rfq.rfq_number} — {rfq.title}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div className="mb-3">
                    <label className="form-label small fw-bold">Detailed Description / Message *</label>
                    <textarea
                      rows={4}
                      className="form-control form-control-sm"
                      placeholder="Please provide full details, dimensions, tolerances, or observations so our engineering team can review..."
                      value={ticketForm.message}
                      onChange={(e) => setTicketForm({ ...ticketForm, message: e.target.value })}
                      required
                      minLength={5}
                    ></textarea>
                  </div>

                  <div className="mb-2">
                    <label className="form-label small fw-bold">
                      Attach Inspection Photos or Reports (Max 2 files, 20 MB each)
                    </label>
                    <input
                      type="file"
                      className="form-control form-control-sm"
                      accept=".jpg,.jpeg,.png,.pdf"
                      multiple
                      onChange={(e) => {
                        const files = Array.from(e.target.files);
                        if (files.length > 2) {
                          setTicketFileError('You can attach at most 2 files per submission.');
                          e.target.value = '';
                          setTicketFiles([]);
                        } else {
                          setTicketFileError('');
                          setTicketFiles(files);
                        }
                      }}
                    />
                    <div className="form-text small text-muted">
                      Accepted formats: JPG, PNG, PDF. Private storage with secure access control.
                    </div>
                  </div>
                </div>

                <div className="modal-footer border-0 pt-0">
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setIsTicketModalOpen(false)}
                    disabled={submittingTicket}
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="btn btn-primary btn-sm fw-bold px-4"
                    disabled={submittingTicket}
                  >
                    {submittingTicket ? 'Submitting Ticket...' : 'Submit Support Ticket'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* TICKET CONVERSATION & RESOLUTION MODAL (SLICE S14) */}
      {isTicketDetailOpen && selectedTicket && (
        <div
          className="modal show d-block"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.70)' }}
          tabIndex="-1"
        >
          <div className="modal-dialog modal-dialog-centered modal-lg modal-dialog-scrollable">
            <div className="modal-content border-0 shadow-lg rounded-4">
              {/* Header */}
              <div className="modal-header border-bottom py-3 bg-light">
                <div>
                  <div className="d-flex align-items-center gap-2 mb-1">
                    <span className="fw-bold font-monospace text-primary fs-5">
                      {selectedTicket.ticket_number}
                    </span>
                    <span
                      className={`badge ${
                        selectedTicket.status === 'open'
                          ? 'bg-primary'
                          : selectedTicket.status === 'in_progress'
                          ? 'bg-warning text-dark'
                          : selectedTicket.status === 'resolved'
                          ? 'bg-success'
                          : 'bg-secondary'
                      }`}
                    >
                      {selectedTicket.status.replace('_', ' ').toUpperCase()}
                    </span>
                    <span className="badge bg-secondary text-uppercase">
                      {selectedTicket.ticket_type.replace('_', ' ')}
                    </span>
                  </div>
                  <h6 className="mb-0 fw-bold text-dark">{selectedTicket.subject}</h6>
                  <div className="text-muted small mt-1">
                    Created: {new Date(selectedTicket.created_at).toLocaleString()}
                    {selectedTicket.order_number && (
                      <span className="ms-2 badge bg-light text-dark border">
                        Linked Order: {selectedTicket.order_number}
                      </span>
                    )}
                    {selectedTicket.rfq_number && (
                      <span className="ms-2 badge bg-light text-dark border">
                        Linked RFQ: {selectedTicket.rfq_number}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  className="btn-close align-self-start"
                  onClick={() => setIsTicketDetailOpen(false)}
                ></button>
              </div>

              {/* Body: Messages Stream & Attachments */}
              <div className="modal-body p-3 p-md-4" style={{ maxHeight: '60vh', overflowY: 'auto' }}>
                {/* Chronological Messages */}
                <div className="d-flex flex-column gap-3 mb-4">
                  {selectedTicket.messages.map((m) => {
                    const isMe = m.sender_role === 'customer';
                    return (
                      <div
                        key={m.id}
                        className={`d-flex flex-column ${isMe ? 'align-items-end' : 'align-items-start'}`}
                      >
                        <div className="small text-muted mb-1 px-1">
                          <strong>{isMe ? 'You (Customer)' : '🛡️ KPC Support Admin'}</strong> ·{' '}
                          {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })},{' '}
                          {new Date(m.created_at).toLocaleDateString()}
                        </div>
                        <div
                          className={`p-3 rounded-3 shadow-sm ${
                            isMe
                              ? 'bg-primary text-white'
                              : 'bg-white border border-secondary-subtle text-dark'
                          }`}
                          style={{ maxWidth: '85%', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}
                        >
                          {m.message}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Attachments Section */}
                {selectedTicket.attachments && selectedTicket.attachments.length > 0 && (
                  <div className="border-top pt-3 mt-3">
                    <h6 className="small fw-bold text-dark mb-2">📎 Attached Verification Documents ({selectedTicket.attachments.length}/2)</h6>
                    <div className="d-flex flex-wrap gap-2">
                      {selectedTicket.attachments.map((att) => (
                        <div
                          key={att.id}
                          className="border rounded-3 p-2 bg-light d-flex align-items-center gap-2 small"
                        >
                          <span className="badge bg-secondary">{getFileExtension(att.file_name)}</span>
                          <span className="fw-semibold text-truncate" style={{ maxWidth: '180px' }} title={att.file_name}>
                            {att.file_name}
                          </span>
                          <span className="text-muted">({formatBytes(att.file_size_bytes)})</span>
                          {att.is_previewable && (
                            <button
                              type="button"
                              className="btn btn-outline-primary btn-sm py-0 px-2"
                              style={{ fontSize: '0.75rem' }}
                              onClick={() =>
                                setPreviewFile({
                                  ticketId: selectedTicket.id,
                                  fileId: att.id,
                                  fileName: att.file_name,
                                  contentType: att.content_type,
                                })
                              }
                            >
                              👁 Preview
                            </button>
                          )}
                          <a
                            href={`${API_BASE}/support/tickets/${selectedTicket.id}/files/${att.id}?disposition=attachment`}
                            download
                            className="btn btn-outline-secondary btn-sm py-0 px-2"
                            style={{ fontSize: '0.75rem' }}
                          >
                            ⬇ Download
                          </a>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Footer: Reply Box */}
              <div className="modal-footer border-top bg-light p-3">
                {selectedTicket.status === 'resolved' || selectedTicket.status === 'closed' ? (
                  <div className="alert alert-secondary py-2 mb-0 w-100 small text-center">
                    <strong>Ticket Closed:</strong> This ticket is currently marked as{' '}
                    <span className="badge bg-success">{selectedTicket.status.toUpperCase()}</span>. Further replies are disabled.
                  </div>
                ) : (
                  <form onSubmit={handleSendTicketReply} className="w-100">
                    <div className="mb-2">
                      <textarea
                        rows={2}
                        className="form-control form-control-sm"
                        placeholder="Type your response to KPC Support..."
                        value={newReply}
                        onChange={(e) => setNewReply(e.target.value)}
                        required
                        disabled={submittingReply}
                      ></textarea>
                    </div>

                    <div className="d-flex justify-content-between align-items-center gap-2">
                      <div className="d-flex align-items-center gap-2">
                        {(!selectedTicket.attachments || selectedTicket.attachments.length < 2) && (
                          <label className="btn btn-outline-secondary btn-sm mb-0" style={{ cursor: 'pointer', fontSize: '0.78rem' }}>
                            📎 {ticketReplyFile ? ticketReplyFile.name : 'Attach File'}
                            <input
                              type="file"
                              className="d-none"
                              accept=".jpg,.jpeg,.png,.pdf"
                              onChange={(e) => setTicketReplyFile(e.target.files[0] || null)}
                            />
                          </label>
                        )}
                        {ticketReplyFile && (
                          <button
                            type="button"
                            className="btn btn-outline-danger btn-sm py-0 px-1"
                            onClick={() => setTicketReplyFile(null)}
                            title="Remove attachment"
                          >
                            ✕
                          </button>
                        )}
                      </div>

                      <div className="d-flex gap-2">
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => setIsTicketDetailOpen(false)}
                          disabled={submittingReply}
                        >
                          Close
                        </button>
                        <button
                          type="submit"
                          className="btn btn-primary btn-sm fw-bold px-3"
                          disabled={submittingReply || !newReply.trim()}
                        >
                          {submittingReply ? 'Sending...' : 'Send Reply'}
                        </button>
                      </div>
                    </div>
                  </form>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
      {/* TAB 3: SUPPORT & INQUIRIES WORKSPACE (SLICE S14) */}
      {activeTab === 'support' && (
        <div>
          <div className="card shadow-sm border-0 rounded-3 mb-4">
            <div className="card-header bg-white border-bottom py-3 d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
              <div>
                <h5 className="card-title h6 mb-1 fw-bold">Support Inquiries & Complaints (Slice S14)</h5>
                <p className="text-muted small mb-0">
                  Direct correspondence with KPC Management for technical pattern requirements, order complaints, and manufacturing queries.
                </p>
              </div>
              <button
                onClick={() => {
                  setTicketForm({ ticket_type: 'inquiry', subject: '', message: '', order_id: '', rfq_id: '' });
                  setTicketFiles([]);
                  setTicketFileError('');
                  fetchCustomerContext();
                  setIsTicketModalOpen(true);
                }}
                className="btn btn-primary btn-sm fw-bold d-flex align-items-center gap-2"
              >
                <span>➕</span> Raise Inquiry / Complaint
              </button>
            </div>

            {/* Filter Toolbar */}
            <div className="card-body bg-light border-bottom py-2">
              <div className="row g-2 align-items-center">
                <div className="col-auto">
                  <span className="small text-secondary fw-bold">Status:</span>
                </div>
                <div className="col-auto d-flex gap-1">
                  {['all', 'open', 'in_progress', 'resolved', 'closed'].map((st) => (
                    <button
                      key={st}
                      type="button"
                      className={`btn btn-sm ${ticketStatusFilter === st ? 'btn-primary' : 'btn-outline-secondary bg-white'}`}
                      style={{ fontSize: '0.8rem', padding: '0.2rem 0.55rem' }}
                      onClick={() => setTicketStatusFilter(st)}
                    >
                      {st === 'all' ? 'All' : st.replace('_', ' ').toUpperCase()}
                    </button>
                  ))}
                </div>

                <div className="col-auto ms-auto d-flex align-items-center gap-2">
                  <span className="small text-secondary fw-bold">Type:</span>
                  <select
                    className="form-select form-select-sm"
                    style={{ width: '160px', fontSize: '0.82rem' }}
                    value={ticketTypeFilter}
                    onChange={(e) => setTicketTypeFilter(e.target.value)}
                  >
                    <option value="all">All Types</option>
                    <option value="inquiry">Inquiry</option>
                    <option value="complaint">Complaint</option>
                    <option value="order_issue">Order Issue</option>
                    <option value="technical_support">Technical Support</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Ticket List */}
            <div className="card-body p-0">
              {loadingTickets ? (
                <div className="p-4 text-center text-muted">
                  <div className="spinner-border spinner-border-sm text-primary me-2"></div>
                  Loading support tickets...
                </div>
              ) : supportTickets.filter((t) => {
                  if (ticketStatusFilter !== 'all' && t.status !== ticketStatusFilter) return false;
                  if (ticketTypeFilter !== 'all' && t.ticket_type !== ticketTypeFilter) return false;
                  return true;
                }).length === 0 ? (
                <div className="p-5 text-center">
                  <div className="display-6 text-muted mb-3">💬</div>
                  <h6 className="fw-bold text-dark">No support tickets found</h6>
                  <p className="text-muted small mb-3">
                    Have a technical question about your casting patterns or need help with an order?
                  </p>
                  <button
                    onClick={() => {
                      fetchCustomerContext();
                      setIsTicketModalOpen(true);
                    }}
                    className="btn btn-outline-primary btn-sm"
                  >
                    Raise Your First Ticket
                  </button>
                </div>
              ) : (
                <div className="table-responsive">
                  <table className="table table-hover align-middle mb-0">
                    <thead className="table-light small text-uppercase">
                      <tr>
                        <th className="ps-3">Ticket #</th>
                        <th>Type</th>
                        <th>Subject</th>
                        <th>Associated Ref</th>
                        <th>Status</th>
                        <th>Messages</th>
                        <th>Last Activity</th>
                        <th className="text-end pe-3">Action</th>
                      </tr>
                    </thead>
                    <tbody className="small">
                      {supportTickets
                        .filter((t) => {
                          if (ticketStatusFilter !== 'all' && t.status !== ticketStatusFilter) return false;
                          if (ticketTypeFilter !== 'all' && t.ticket_type !== ticketTypeFilter) return false;
                          return true;
                        })
                        .map((t) => (
                          <tr key={t.id}>
                            <td className="ps-3 fw-bold text-primary font-monospace">{t.ticket_number}</td>
                            <td>
                              <span
                                className={`badge ${
                                  t.ticket_type === 'complaint'
                                    ? 'bg-danger'
                                    : t.ticket_type === 'order_issue'
                                    ? 'bg-warning text-dark'
                                    : t.ticket_type === 'technical_support'
                                    ? 'bg-primary'
                                    : 'bg-info text-dark'
                                }`}
                              >
                                {t.ticket_type.replace('_', ' ').toUpperCase()}
                              </span>
                            </td>
                            <td>
                              <span className="fw-bold text-dark">{t.subject}</span>
                            </td>
                            <td>
                              {t.order_number ? (
                                <span className="badge bg-secondary font-monospace">ORD: {t.order_number}</span>
                              ) : t.rfq_number ? (
                                <span className="badge bg-light text-dark border font-monospace">RFQ: {t.rfq_number}</span>
                              ) : (
                                <span className="text-muted small">—</span>
                              )}
                            </td>
                            <td>
                              <span
                                className={`badge ${
                                  t.status === 'open'
                                    ? 'bg-primary'
                                    : t.status === 'in_progress'
                                    ? 'bg-warning text-dark'
                                    : t.status === 'resolved'
                                    ? 'bg-success'
                                    : 'bg-secondary'
                                }`}
                              >
                                {t.status.replace('_', ' ').toUpperCase()}
                              </span>
                            </td>
                            <td>
                              <span className="badge bg-light text-dark border">
                                💬 {t.message_count}
                              </span>
                            </td>
                            <td className="text-muted">
                              {new Date(t.updated_at).toLocaleDateString()}
                            </td>
                            <td className="text-end pe-3">
                              <button
                                onClick={() => handleOpenTicket(t.id)}
                                className="btn btn-outline-primary btn-sm fw-bold"
                              >
                                Open Conversation
                              </button>
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <PasswordChangeModal
        isOpen={isPasswordModalOpen}
        onClose={() => setIsPasswordModalOpen(false)}
      />
    </PortalLayout>
  );
}
