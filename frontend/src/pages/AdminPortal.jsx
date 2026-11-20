import AdminOrdersPanel from '../components/commercial/AdminOrdersPanel';
import AdminInvoicesPanel from '../components/commercial/AdminInvoicesPanel';
import { QuotationWorkspace } from '../components/QuotationWorkspace';
import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { AdminLayout, adminPages } from '../components/AdminLayout';
import { AdminDashboard, AdminUnavailable } from '../components/AdminDashboard';
import { AdminCatalogue } from './AdminCatalogue';
import { PasswordChangeModal } from '../components/PasswordChangeModal';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export function AdminPortal() {
  const { user, csrfToken } = useAuth();
  const [quotationRfq, setQuotationRfq] = useState(null);
  const [activeTab, setActiveTab] = useState(() => { const tab = new URLSearchParams(window.location.search).get('tab'); return adminPages.some(page => page.id === tab) ? tab : 'dashboard'; });
  const [dashboardSearch, setDashboardSearch] = useState('');
  function navigateTab(tab) {
    setQuotationRfq(null);
    setActiveTab(tab);
    setFeedback({ error: '', success: '' });
    const url = new URL(window.location.href);
    url.searchParams.set('tab', tab);
    window.history.replaceState(null, '', url);
  }

  // Users State (S02)
  const [users, setUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [roleFilter, setRoleFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // RFQs State (S05)
  const [rfqs, setRfqs] = useState([]);
  const [loadingRfqs, setLoadingRfqs] = useState(false);
  const [rfqStatusFilter, setRfqStatusFilter] = useState('');
  const [rfqTypeFilter, setRfqTypeFilter] = useState('');
  const [rfqSearchQuery, setRfqSearchQuery] = useState('');
  const [selectedRfqModal, setSelectedRfqModal] = useState(null);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [previewFile, setPreviewFile] = useState(null);

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

  // Common Feedback State
  const [feedback, setFeedback] = useState({ error: '', success: '' });

  // Modals state
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const [isEmployeeModalOpen, setIsEmployeeModalOpen] = useState(false);
  const [isResetModalOpen, setIsResetModalOpen] = useState(false);
  const [targetUserForReset, setTargetUserForReset] = useState(null);
  const [newResetPassword, setNewResetPassword] = useState('');

  // New Employee Form State
  const [employeeForm, setEmployeeForm] = useState({
    email: '',
    password: '',
    full_name: '',
    department: '',
    phone: '',
  });
  const [submittingEmp, setSubmittingEmp] = useState(false);

  // Support Tickets Queue (Slice S14)
  const [adminTickets, setAdminTickets] = useState([]);
  const [loadingAdminTickets, setLoadingAdminTickets] = useState(false);
  const [selectedAdminTicket, setSelectedAdminTicket] = useState(null);
  const [isAdminTicketModalOpen, setIsAdminTicketModalOpen] = useState(false);
  const [adminTicketFilter, setAdminTicketFilter] = useState('all');
  const [adminTicketTypeFilter, setAdminTicketTypeFilter] = useState('all');
  const [adminSearch, setAdminSearch] = useState('');
  const [adminReplyText, setAdminReplyText] = useState('');
  const [submittingAdminReply, setSubmittingAdminReply] = useState(false);
  const [adminStatusUpdate, setAdminStatusUpdate] = useState('');
  const [updatingTicketStatus, setUpdatingTicketStatus] = useState(false);

  useEffect(() => {
    if (activeTab === 'users') {
      fetchUsers();
    } else if (activeTab === 'rfqs') {
      fetchRfqs();
    } else if (activeTab === 'support') {
      fetchAdminTickets();
    }
  }, [activeTab, roleFilter, rfqStatusFilter, rfqTypeFilter, adminTicketFilter, adminTicketTypeFilter]);

  async function fetchAdminTickets() {
    setLoadingAdminTickets(true);
    try {
      const params = new URLSearchParams();
      if (adminTicketFilter !== 'all') params.append('status', adminTicketFilter);
      if (adminTicketTypeFilter !== 'all') params.append('ticket_type', adminTicketTypeFilter);
      if (adminSearch.trim()) params.append('search', adminSearch.trim());

      const res = await fetch(`${API_BASE}/admin/support/tickets?${params.toString()}`, { credentials: 'same-origin' });
      if (res.ok) {
        const data = await res.json();
        setAdminTickets(data);
      }
    } catch (err) {
      console.error('Failed to load admin support tickets:', err);
    } finally {
      setLoadingAdminTickets(false);
    }
  }

  async function handleOpenAdminTicket(ticketId) {
    try {
      const res = await fetch(`${API_BASE}/support/tickets/${ticketId}`, { credentials: 'same-origin' });
      if (res.ok) {
        const data = await res.json();
        setSelectedAdminTicket(data);
        setAdminStatusUpdate(data.status);
        setIsAdminTicketModalOpen(true);
        setAdminReplyText('');
      } else {
        const err = await res.json().catch(() => ({}));
        setFeedback({ error: err.detail || 'Failed to open ticket details.', success: '' });
      }
    } catch (err) {
      setFeedback({ error: 'Failed to retrieve ticket conversation.', success: '' });
    }
  }

  async function handleSendAdminReply(e) {
    e.preventDefault();
    if (!adminReplyText.trim() || !selectedAdminTicket) return;

    setSubmittingAdminReply(true);
    try {
      const res = await fetch(`${API_BASE}/support/tickets/${selectedAdminTicket.id}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken || '',
        },
        credentials: 'same-origin',
        body: JSON.stringify({ message: adminReplyText.trim() }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to send admin response.');
      }

      setAdminReplyText('');
      await handleOpenAdminTicket(selectedAdminTicket.id);
      fetchAdminTickets();
    } catch (err) {
      alert(err.message);
    } finally {
      setSubmittingAdminReply(false);
    }
  }

  async function handleAdminStatusChange(newStatus) {
    if (!selectedAdminTicket || !newStatus) return;
    setUpdatingTicketStatus(true);
    try {
      const res = await fetch(`${API_BASE}/admin/support/tickets/${selectedAdminTicket.id}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken || '',
        },
        credentials: 'same-origin',
        body: JSON.stringify({ status: newStatus }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to update ticket status.');
      }

      const updated = await res.json();
      setSelectedAdminTicket((prev) => ({ ...prev, status: updated.status }));
      setAdminStatusUpdate(updated.status);
      fetchAdminTickets();
    } catch (err) {
      alert(err.message);
    } finally {
      setUpdatingTicketStatus(false);
    }
  }

  async function fetchUsers() {
    setLoadingUsers(true);
    try {
      let url = `${API_BASE}/admin/users`;
      const params = new URLSearchParams();
      if (roleFilter) params.append('role', roleFilter);
      if (searchQuery) params.append('search', searchQuery);
      if (params.toString()) url += `?${params.toString()}`;

      const res = await fetch(url, { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Failed to load user records.');
      const data = await res.json();
      setUsers(data);
    } catch (err) {
      setFeedback({ error: err.message, success: '' });
    } finally {
      setLoadingUsers(false);
    }
  }

  async function fetchRfqs() {
    setLoadingRfqs(true);
    try {
      let url = `${API_BASE}/admin/rfqs`;
      const params = new URLSearchParams();
      if (rfqStatusFilter) params.append('status', rfqStatusFilter);
      if (rfqTypeFilter) params.append('rfq_type', rfqTypeFilter);
      if (rfqSearchQuery) params.append('search', rfqSearchQuery);
      if (params.toString()) url += `?${params.toString()}`;

      const res = await fetch(url, { credentials: 'same-origin' });
      if (!res.ok) throw new Error('Failed to load incoming RFQs.');
      const data = await res.json();
      setRfqs(data);
    } catch (err) {
      setFeedback({ error: err.message, success: '' });
    } finally {
      setLoadingRfqs(false);
    }
  }

  async function handleUpdateRfqStatus(rfqId, nextStatus) {
    setUpdatingStatus(true);
    try {
      const res = await fetch(`${API_BASE}/admin/rfqs/${rfqId}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken || '',
        },
        credentials: 'same-origin',
        body: JSON.stringify({ status: nextStatus }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail?.message || 'Failed to update RFQ review status.');
      }

      const updated = await res.json();
      setSelectedRfqModal(updated);
      setFeedback({
        error: '',
        success: `RFQ ${updated.rfq_number} updated to "${nextStatus.replace('_', ' ').toUpperCase()}".`,
      });
      fetchRfqs();
    } catch (err) {
      setFeedback({ error: err.message, success: '' });
    } finally {
      setUpdatingStatus(false);
    }
  }

  async function handleToggleStatus(targetUser) {
    const newStatus = !targetUser.is_active;
    const confirmMsg = newStatus
      ? `Re-activate account for ${targetUser.email}?`
      : `Deactivate ${targetUser.email}? This will IMMEDIATELY terminate all active sessions for this user.`;

    if (!window.confirm(confirmMsg)) return;

    try {
      const res = await fetch(`${API_BASE}/admin/users/${targetUser.id}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken || '',
        },
        credentials: 'same-origin',
        body: JSON.stringify({ is_active: newStatus }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail?.message || 'Failed to update account status.');
      }

      setFeedback({
        error: '',
        success: `Account ${targetUser.email} ${newStatus ? 'activated' : 'deactivated (sessions terminated)'}.`,
      });
      fetchUsers();
    } catch (err) {
      setFeedback({ error: err.message, success: '' });
    }
  }

  async function handleResetPasswordSubmit(e) {
    e.preventDefault();
    if (!newResetPassword || newResetPassword.length < 8) {
      setFeedback({ error: 'Password must be at least 8 characters long.', success: '' });
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/admin/users/${targetUserForReset.id}/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken || '',
        },
        credentials: 'same-origin',
        body: JSON.stringify({ new_password: newResetPassword }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail?.message || 'Password reset failed.');
      }

      setFeedback({
        error: '',
        success: `Password reset successfully for ${targetUserForReset.email}. All previous sessions revoked; user must set new password on next login.`,
      });
      setIsResetModalOpen(false);
      setTargetUserForReset(null);
      setNewResetPassword('');
      fetchUsers();
    } catch (err) {
      setFeedback({ error: err.message, success: '' });
    }
  }

  async function handleCreateEmployeeSubmit(e) {
    e.preventDefault();
    setSubmittingEmp(true);
    setFeedback({ error: '', success: '' });

    try {
      const res = await fetch(`${API_BASE}/admin/users/employee`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrfToken || '',
        },
        credentials: 'same-origin',
        body: JSON.stringify(employeeForm),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail?.message || 'Failed to create employee account.');
      }

      setFeedback({
        error: '',
        success: `Employee ${employeeForm.email} provisioned successfully with temporary password!`,
      });
      setIsEmployeeModalOpen(false);
      setEmployeeForm({ email: '', password: '', full_name: '', department: '', phone: '' });
      fetchUsers();
    } catch (err) {
      setFeedback({ error: err.message, success: '' });
    } finally {
      setSubmittingEmp(false);
    }
  }

  return (
    <AdminLayout activeTab={activeTab} onNavigate={navigateTab} search={dashboardSearch} onSearch={setDashboardSearch} onPassword={() => setIsPasswordModalOpen(true)}>
      {feedback.success && (
        <div className="alert alert-success alert-dismissible fade show small py-2 mb-3" role="alert">
          {feedback.success}
          <button
            type="button"
            className="btn-close" aria-label="Close"
            onClick={() => setFeedback({ ...feedback, success: '' })}
          ></button>
        </div>
      )}

      {feedback.error && (
        <div className="alert alert-danger alert-dismissible fade show small py-2 mb-3" role="alert">
          {feedback.error}
          <button
            type="button"
            className="btn-close" aria-label="Close"
            onClick={() => setFeedback({ ...feedback, error: '' })}
          ></button>
        </div>
      )}

      {activeTab === 'dashboard' && <AdminDashboard search={dashboardSearch} onNavigate={navigateTab} onOpenRfq={rfq => { navigateTab('rfqs'); setSelectedRfqModal(rfq); }} onOpenTicket={id => { navigateTab('support'); handleOpenAdminTicket(id); }} />}
      {['inventory', 'reports'].includes(activeTab) && <AdminUnavailable title={adminPages.find(page => page.id === activeTab)?.title} onSupport={() => navigateTab('support')} />}

      {activeTab === 'orders' && <AdminOrdersPanel />}
      {activeTab === 'invoices' && <AdminInvoicesPanel />}
      {activeTab === 'catalogue' && <AdminCatalogue />}

      {/* TAB 1: RFQ REVIEW QUEUE (SLICE S05) */}
      {quotationRfq && activeTab === 'rfqs' && <QuotationWorkspace rfq={quotationRfq} admin csrfToken={csrfToken} onBack={() => setQuotationRfq(null)} onIssued={fetchRfqs} />}
      {!quotationRfq && activeTab === 'rfqs' && (
        <div className="card shadow-sm border-0 rounded-3 mb-4">
          <div className="card-header bg-white border-bottom py-3 d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
            <div>
              <h5 className="card-title h6 mb-1 fw-bold">Incoming Customer RFQs & Pattern Specifications</h5>
              <p className="text-muted small mb-0">
                Review technical requirements submitted by B2B clients before quotation and estimation.
              </p>
            </div>
          </div>

          {/* Filters Toolbar */}
          <div className="card-body border-bottom bg-light py-3">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                fetchRfqs();
              }}
              className="row g-2 align-items-center"
            >
              <div className="col-12 col-sm-3 col-md-2">
                <select
                  className="form-select form-select-sm"
                  value={rfqStatusFilter}
                  onChange={(e) => setRfqStatusFilter(e.target.value)}
                >
                  <option value="">All Statuses</option>
                  <option value="submitted">Submitted</option>
                  <option value="under_review">Under Review</option>
                  <option value="quoted">Quoted</option>
                  <option value="closed">Closed</option>
                </select>
              </div>

              <div className="col-12 col-sm-3 col-md-2">
                <select
                  className="form-select form-select-sm"
                  value={rfqTypeFilter}
                  onChange={(e) => setRfqTypeFilter(e.target.value)}
                >
                  <option value="">All Types</option>
                  <option value="custom">Custom Pattern</option>
                  <option value="standard">Standard Pattern</option>
                </select>
              </div>

              <div className="col-12 col-sm-4 col-md-6">
                <input
                  type="text"
                  className="form-control form-control-sm"
                  placeholder="Search by RFQ number, company, or part name…"
                  value={rfqSearchQuery}
                  onChange={(e) => setRfqSearchQuery(e.target.value)}
                />
              </div>

              <div className="col-12 col-sm-2 col-md-2">
                <button type="submit" className="btn btn-secondary btn-sm w-100">
                  Filter
                </button>
              </div>
            </form>
          </div>

          {/* RFQ Table */}
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light small">
                <tr>
                  <th>RFQ Reference</th>
                  <th>Customer / Company</th>
                  <th>Pattern Title</th>
                  <th>Type</th>
                  <th>Material</th>
                  <th>Quantity</th>
                  <th>Submitted</th>
                  <th>Status</th>
                  <th className="text-end">Actions</th>
                </tr>
              </thead>
              <tbody className="small">
                {loadingRfqs ? (
                  <tr>
                    <td colSpan="9" className="text-center py-4 text-muted">
                      Loading incoming RFQs…
                    </td>
                  </tr>
                ) : rfqs.length === 0 ? (
                  <tr>
                    <td colSpan="9" className="text-center py-4 text-muted">
                      No customer RFQs found matching the filter criteria.
                    </td>
                  </tr>
                ) : (
                  rfqs.map((rfq) => (
                    <tr key={rfq.id}>
                      <td>
                        <span className="fw-bold text-dark">{rfq.rfq_number}</span>
                      </td>
                      <td>
                        <strong className="d-block">{rfq.customer_company || 'Client'}</strong>
                        <span className="text-muted small">{rfq.customer_email}</span>
                      </td>
                      <td className="fw-semibold text-dark">{rfq.title}</td>
                      <td>
                        <span
                          className={`badge text-uppercase ${
                            rfq.rfq_type === 'standard' ? 'bg-secondary' : 'bg-primary'
                          }`}
                        >
                          {rfq.rfq_type}
                        </span>
                      </td>
                      <td>{rfq.material}</td>
                      <td>
                        <span className="badge bg-light text-dark border">{rfq.quantity} pcs</span>
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
                          onClick={() => setSelectedRfqModal(rfq)}
                          className="btn btn-outline-primary btn-sm"
                        >
                          Inspect Specs
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 2: USER & EMPLOYEE ACCOUNTS (SLICE S02) */}
      {activeTab === 'users' && (
        <div className="card shadow-sm border-0 rounded-3 mb-4">
          <div className="card-header bg-white border-bottom py-3 d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
            <div>
              <h5 className="card-title h6 mb-1 fw-bold">Users & account access</h5>
              <p className="text-muted small mb-0">
                Manage Customer and Employee accounts, deactivate compromised logins, and perform credential resets.
              </p>
            </div>
            <div className="d-flex gap-2">
              <button
                onClick={() => setIsEmployeeModalOpen(true)}
                className="btn btn-primary btn-sm fw-bold"
              >
                + Create Employee Account
              </button>
            </div>
          </div>

          {/* Filters Toolbar */}
          <div className="card-body border-bottom bg-light py-3">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                fetchUsers();
              }}
              className="row g-2 align-items-center"
            >
              <div className="col-12 col-sm-4 col-md-3">
                <select
                  className="form-select form-select-sm"
                  value={roleFilter}
                  onChange={(e) => setRoleFilter(e.target.value)}
                >
                  <option value="">All Roles</option>
                  <option value="customer">Customers</option>
                  <option value="employee">Employees</option>
                  <option value="admin">Administrators</option>
                </select>
              </div>
              <div className="col-12 col-sm-6 col-md-5">
                <input
                  type="text"
                  className="form-control form-control-sm"
                  placeholder="Search email, company, staff name…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <div className="col-12 col-sm-2 col-md-2">
                <button type="submit" className="btn btn-secondary btn-sm w-100">
                  Search
                </button>
              </div>
            </form>
          </div>

          {/* Users Table */}
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light small">
                <tr>
                  <th>User / Email</th>
                  <th>Role</th>
                  <th>Identity / Profile</th>
                  <th>Status</th>
                  <th>Sessions</th>
                  <th>Joined</th>
                  <th className="text-end">Actions</th>
                </tr>
              </thead>
              <tbody className="small">
                {loadingUsers ? (
                  <tr>
                    <td colSpan="7" className="text-center py-4 text-muted">
                      Loading accounts…
                    </td>
                  </tr>
                ) : users.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="text-center py-4 text-muted">
                      No accounts found matching your filter criteria.
                    </td>
                  </tr>
                ) : (
                  users.map((item) => {
                    const isCurrentAdmin = item.id === user?.id;
                    const displayName =
                      item.role === 'customer'
                        ? item.customer_profile?.company_name || 'Individual'
                        : item.role === 'employee'
                        ? `${item.employee_profile?.full_name || 'Staff'} (${item.employee_profile?.department || 'Production'})`
                        : 'KPC Administrator';

                    return (
                      <tr key={item.id}>
                        <td>
                          <span className="fw-bold d-block text-dark">{item.email}</span>
                          {item.must_change_password && (
                            <span className="badge bg-warning text-dark me-1">Temporary Password</span>
                          )}
                        </td>
                        <td>
                          <span
                            className={`badge text-uppercase ${
                              item.role === 'admin'
                                ? 'bg-danger'
                                : item.role === 'employee'
                                ? 'bg-info text-dark'
                                : 'bg-primary'
                            }`}
                          >
                            {item.role}
                          </span>
                        </td>
                        <td>
                          <span>{displayName}</span>
                          {item.customer_profile?.contact_person && (
                            <span className="d-block text-muted small">
                              Attn: {item.customer_profile.contact_person}
                            </span>
                          )}
                        </td>
                        <td>
                          {item.is_active ? (
                            <span className="badge bg-success">Active</span>
                          ) : (
                            <span className="badge bg-secondary">Deactivated</span>
                          )}
                        </td>
                        <td>
                          <span className="badge bg-light text-dark border">
                            {item.active_sessions_count} active
                          </span>
                        </td>
                        <td className="text-muted">
                          {new Date(item.created_at).toLocaleDateString()}
                        </td>
                        <td className="text-end">
                          <div className="btn-group btn-group-sm">
                            <button
                              type="button"
                              className="btn btn-outline-secondary"
                              onClick={() => {
                                setTargetUserForReset(item);
                                setIsResetModalOpen(true);
                              }}
                              title="Reset Password"
                            >
                              Reset Pwd
                            </button>
                            {!isCurrentAdmin && (
                              <button
                                type="button"
                                className={`btn ${item.is_active ? 'btn-outline-danger' : 'btn-outline-success'}`}
                                onClick={() => handleToggleStatus(item)}
                              >
                                {item.is_active ? 'Deactivate' : 'Activate'}
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: SUPPORT TICKETS QUEUE (SLICE S14) */}
      {activeTab === 'support' && (
        <div className="card shadow-sm border-0 rounded-3 mb-4">
          <div className="card-header bg-white border-bottom py-3 d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
            <div>
              <h5 className="card-title h6 mb-1 fw-bold">Customer support tickets</h5>
              <p className="text-muted small mb-0">
                Review and resolve customer inquiries, pattern dimensional disputes, and technical support conversations.
              </p>
            </div>
            <button
              onClick={() => fetchAdminTickets()}
              className="btn btn-outline-secondary btn-sm d-flex align-items-center gap-1"
            >
              🔄 Refresh Queue
            </button>
          </div>

          {/* Filter Bar */}
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
                    className={`btn btn-sm ${adminTicketFilter === st ? 'btn-primary' : 'btn-outline-secondary bg-white'}`}
                    style={{ fontSize: '0.8rem', padding: '0.2rem 0.55rem' }}
                    onClick={() => setAdminTicketFilter(st)}
                  >
                    {st === 'all' ? 'All' : st.replace('_', ' ').toUpperCase()}
                  </button>
                ))}
              </div>

              <div className="col-auto ms-md-auto d-flex align-items-center gap-2">
                <span className="small text-secondary fw-bold">Type:</span>
                <select
                  className="form-select form-select-sm"
                  style={{ width: '150px', fontSize: '0.82rem' }}
                  value={adminTicketTypeFilter}
                  onChange={(e) => setAdminTicketTypeFilter(e.target.value)}
                >
                  <option value="all">All Types</option>
                  <option value="inquiry">Inquiry</option>
                  <option value="complaint">Complaint</option>
                  <option value="order_issue">Order Issue</option>
                  <option value="technical_support">Technical Support</option>
                </select>

                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    fetchAdminTickets();
                  }}
                  className="d-flex align-items-center gap-1"
                >
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    placeholder="Search ticket # or subject..."
                    style={{ width: '190px', fontSize: '0.82rem' }}
                    value={adminSearch}
                    onChange={(e) => setAdminSearch(e.target.value)}
                  />
                  <button type="submit" className="btn btn-outline-primary btn-sm py-1">
                    🔍
                  </button>
                </form>
              </div>
            </div>
          </div>

          {/* Queue Table */}
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead className="table-light small text-uppercase">
                <tr>
                  <th className="ps-3">Ticket #</th>
                  <th>Customer</th>
                  <th>Type</th>
                  <th>Subject</th>
                  <th>Associated Reference</th>
                  <th>Status</th>
                  <th>Messages</th>
                  <th>Last Activity</th>
                  <th className="text-end pe-3">Actions</th>
                </tr>
              </thead>
              <tbody className="small">
                {loadingAdminTickets ? (
                  <tr>
                    <td colSpan="9" className="text-center py-4 text-muted">
                      <div className="spinner-border spinner-border-sm text-primary me-2"></div>
                      Loading support tickets queue...
                    </td>
                  </tr>
                ) : adminTickets.length === 0 ? (
                  <tr>
                    <td colSpan="9" className="text-center py-5 text-muted">
                      No support tickets found matching current filters.
                    </td>
                  </tr>
                ) : (
                  adminTickets.map((t) => (
                    <tr key={t.id}>
                      <td className="ps-3 fw-bold text-primary font-monospace">{t.ticket_number}</td>
                      <td>
                        <span className="fw-bold d-block text-dark">{t.customer_name || 'Customer'}</span>
                        <span className="text-muted small">{t.customer_email}</span>
                      </td>
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
                          onClick={() => handleOpenAdminTicket(t.id)}
                          className="btn btn-outline-primary btn-sm fw-bold"
                        >
                          Manage & Reply
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* INSPECT RFQ SPECS MODAL (SLICE S05) */}
      {selectedRfqModal && (
        <div
          className="modal show d-block"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.65)' }}
          tabIndex="-1"
        >
          <div className="modal-dialog modal-dialog-centered modal-lg">
            <div className="modal-content border-0 shadow-lg rounded-4 p-3 p-md-4">
              <div className="modal-header border-0 pb-2">
                <div>
                  <span className="badge bg-primary text-uppercase me-2">{selectedRfqModal.rfq_type}</span>
                  <span className="badge bg-warning text-dark text-uppercase">{selectedRfqModal.status.replace('_', ' ')}</span>
                  <h4 className="modal-title fw-bold mt-2">{selectedRfqModal.title}</h4>
                  <p className="text-muted small mb-0">Reference: {selectedRfqModal.rfq_number}</p>
                </div>
                <button
                  type="button"
                  className="btn-close" aria-label="Close"
                  onClick={() => setSelectedRfqModal(null)}
                ></button>
              </div>

              <div className="modal-body">
                {/* Client Company Fact Card */}
                <div className="alert alert-light border rounded-3 p-3 mb-3 small">
                  <h6 className="fw-bold mb-1">Customer Client Details</h6>
                  <div className="row g-2">
                    <div className="col-md-6"><strong>Company:</strong> {selectedRfqModal.customer_company || 'Not specified'}</div>
                    <div className="col-md-6"><strong>Contact Person:</strong> {selectedRfqModal.customer_contact || selectedRfqModal.customer_email}</div>
                    <div className="col-md-6"><strong>Email:</strong> {selectedRfqModal.customer_email}</div>
                    <div className="col-md-6"><strong>Phone:</strong> {selectedRfqModal.customer_phone || 'Not provided'}</div>
                  </div>
                </div>

                <div className="row g-3 small">
                  <div className="col-md-6">
                    <p className="mb-1 text-muted">Material Specified</p>
                    <h6 className="fw-bold">{selectedRfqModal.material}</h6>
                  </div>
                  <div className="col-md-6">
                    <p className="mb-1 text-muted">Order Quantity</p>
                    <h6 className="fw-bold">{selectedRfqModal.quantity} pieces</h6>
                  </div>
                  <div className="col-md-6">
                    <p className="mb-1 text-muted">Dimensions</p>
                    <p className="fw-semibold">{selectedRfqModal.dimensions || 'As per CAD drawing'}</p>
                  </div>
                  <div className="col-md-6">
                    <p className="mb-1 text-muted">Target Delivery Date</p>
                    <p className="fw-semibold">{selectedRfqModal.target_delivery_date || 'Standard delivery'}</p>
                  </div>
                  {selectedRfqModal.specifications && (
                    <div className="col-12">
                      <p className="mb-1 text-muted">Technical Tolerances / Allowances</p>
                      <p className="p-2 bg-light rounded">{selectedRfqModal.specifications}</p>
                    </div>
                  )}
                  {selectedRfqModal.description && (
                    <div className="col-12">
                      <p className="mb-1 text-muted">Description & Casting Process</p>
                      <p className="p-2 bg-light rounded">{selectedRfqModal.description}</p>
                    </div>
                  )}
                  {selectedRfqModal.notes && (
                    <div className="col-12">
                      <p className="mb-1 text-muted">Tooling Notes</p>
                      <p className="p-2 bg-light rounded">{selectedRfqModal.notes}</p>
                    </div>
                  )}

                  {/* S06 Attached Files Inspection for Admin */}
                  <div className="col-12 mt-3 pt-3 border-top">
                    <h6 className="fw-bold small text-dark mb-2">
                      Attached CAD Drawings & Technical Blueprints ({selectedRfqModal.files?.length || 0}/2)
                    </h6>
                    {!selectedRfqModal.files || selectedRfqModal.files.length === 0 ? (
                      <p className="small text-muted mb-0">
                        No CAD models or blueprint documents attached to this customer RFQ.
                      </p>
                    ) : (
                      <div className="list-group">
                        {selectedRfqModal.files.map((file) => (
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
                                      rfqId: selectedRfqModal.id,
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
                                href={`${API_BASE}/rfqs/${selectedRfqModal.id}/files/${file.id}?disposition=attachment`}
                                className="btn btn-sm btn-outline-secondary py-0 px-2"
                                download
                              >
                                ⬇ Download
                              </a>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Status Transition Control */}
                <div className="card bg-light border-0 p-3 mt-4 rounded-3">
                  <h6 className="fw-bold small mb-2">Review Status Action:</h6>
                  <div className="d-flex gap-2">
                    {selectedRfqModal.status === 'submitted' && (
                      <button
                        onClick={() => handleUpdateRfqStatus(selectedRfqModal.id, 'under_review')}
                        className="btn btn-warning btn-sm fw-bold"
                        disabled={updatingStatus}
                      >
                        {updatingStatus ? 'Updating…' : 'Mark as Under Review'}
                      </button>
                    )}
                    {selectedRfqModal.status === 'under_review' && (
                      <span className="badge bg-warning text-dark align-self-center py-2 px-3">
                        Under Review by Engineering
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="modal-footer border-0">
                <button className="btn btn-primary" onClick={() => { setQuotationRfq(selectedRfqModal); setSelectedRfqModal(null); }}>Create / review quotation</button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => setSelectedRfqModal(null)}
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create Employee Modal */}
      {isEmployeeModalOpen && (
        <div
          className="modal show d-block"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.65)' }}
          tabIndex="-1"
        >
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow-lg rounded-4 p-3">
              <div className="modal-header border-0 pb-0">
                <h5 className="modal-title fw-bold">Provision Employee Account</h5>
                <button
                  type="button"
                  className="btn-close" aria-label="Close"
                  onClick={() => setIsEmployeeModalOpen(false)}
                  disabled={submittingEmp}
                ></button>
              </div>
              <div className="modal-body">
                <form onSubmit={handleCreateEmployeeSubmit}>
                  <div className="mb-2">
                    <label className="form-label small fw-bold mb-1">Staff Full Name</label>
                    <input
                      type="text"
                      className="form-control form-control-sm"
                      placeholder="Kishan Dave"
                      value={employeeForm.full_name}
                      onChange={(e) =>
                        setEmployeeForm({ ...employeeForm, full_name: e.target.value })
                      }
                      required
                    />
                  </div>

                  <div className="mb-2">
                    <label className="form-label small fw-bold mb-1">Employee Work Email</label>
                    <input
                      type="email"
                      className="form-control form-control-sm"
                      placeholder="kishan@kpc.com"
                      value={employeeForm.email}
                      onChange={(e) =>
                        setEmployeeForm({ ...employeeForm, email: e.target.value })
                      }
                      required
                    />
                  </div>

                  <div className="mb-2">
                    <label className="form-label small fw-bold mb-1">Department</label>
                    <input
                      type="text"
                      className="form-control form-control-sm"
                      placeholder="Machining & CNC Tooling"
                      value={employeeForm.department}
                      onChange={(e) =>
                        setEmployeeForm({ ...employeeForm, department: e.target.value })
                      }
                    />
                  </div>

                  <div className="mb-2">
                    <label className="form-label small fw-bold mb-1">Phone Number</label>
                    <input
                      type="tel"
                      className="form-control form-control-sm"
                      placeholder="+91 98123 45678"
                      value={employeeForm.phone}
                      onChange={(e) =>
                        setEmployeeForm({ ...employeeForm, phone: e.target.value })
                      }
                    />
                  </div>

                  <div className="mb-4">
                    <label className="form-label small fw-bold mb-1">Initial Temporary Password</label>
                    <input
                      type="password"
                      className="form-control form-control-sm"
                      placeholder="Min 8 characters"
                      value={employeeForm.password}
                      onChange={(e) =>
                        setEmployeeForm({ ...employeeForm, password: e.target.value })
                      }
                      required
                    />
                    <span className="text-muted small">
                      Employee will be forced to change this password on initial sign in.
                    </span>
                  </div>

                  <div className="d-flex justify-content-end gap-2">
                    <button
                      type="button"
                      className="btn btn-outline-secondary btn-sm"
                      onClick={() => setIsEmployeeModalOpen(false)}
                      disabled={submittingEmp}
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="btn btn-primary btn-sm fw-bold"
                      disabled={submittingEmp}
                    >
                      {submittingEmp ? 'Provisioning…' : 'Create Employee'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Admin Reset Password Modal */}
      {isResetModalOpen && targetUserForReset && (
        <div
          className="modal show d-block"
          style={{ backgroundColor: 'rgba(15, 23, 42, 0.65)' }}
          tabIndex="-1"
        >
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content border-0 shadow-lg rounded-4 p-3">
              <div className="modal-header border-0 pb-0">
                <h5 className="modal-title fw-bold">Reset Password</h5>
                <button
                  type="button"
                  className="btn-close" aria-label="Close"
                  onClick={() => {
                    setIsResetModalOpen(false);
                    setTargetUserForReset(null);
                  }}
                ></button>
              </div>
              <div className="modal-body">
                <p className="small text-secondary mb-3">
                  Resetting password for <strong>{targetUserForReset.email}</strong>. This will
                  immediately terminate all existing sessions for this user and require them to set a
                  new password upon login.
                </p>

                <form onSubmit={handleResetPasswordSubmit}>
                  <div className="mb-4">
                    <label className="form-label small fw-bold mb-1">New Temporary Password</label>
                    <input
                      type="password"
                      className="form-control"
                      placeholder="At least 8 characters"
                      value={newResetPassword}
                      onChange={(e) => setNewResetPassword(e.target.value)}
                      required
                    />
                  </div>

                  <div className="d-flex justify-content-end gap-2">
                    <button
                      type="button"
                      className="btn btn-outline-secondary btn-sm"
                      onClick={() => {
                        setIsResetModalOpen(false);
                        setTargetUserForReset(null);
                      }}
                    >
                      Cancel
                    </button>
                    <button type="submit" className="btn btn-danger btn-sm fw-bold">
                      Confirm Reset
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* IN-BROWSER FILE PREVIEW MODAL FOR ADMIN (SLICE S06) */}
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
                    ⬇ Download File
                  </a>
                  <button
                    type="button"
                    className="btn-close" aria-label="Close"
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

      {/* ADMIN SUPPORT TICKET RESOLUTION MODAL (SLICE S14) */}
      {isAdminTicketModalOpen && selectedAdminTicket && (
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
                      {selectedAdminTicket.ticket_number}
                    </span>
                    <span
                      className={`badge ${
                        selectedAdminTicket.status === 'open'
                          ? 'bg-primary'
                          : selectedAdminTicket.status === 'in_progress'
                          ? 'bg-warning text-dark'
                          : selectedAdminTicket.status === 'resolved'
                          ? 'bg-success'
                          : 'bg-secondary'
                      }`}
                    >
                      {selectedAdminTicket.status.replace('_', ' ').toUpperCase()}
                    </span>
                    <span className="badge bg-secondary text-uppercase">
                      {selectedAdminTicket.ticket_type.replace('_', ' ')}
                    </span>
                  </div>
                  <h6 className="mb-0 fw-bold text-dark">{selectedAdminTicket.subject}</h6>
                  <div className="text-muted small mt-1">
                    Customer: <strong className="text-dark">{selectedAdminTicket.customer_name}</strong> ({selectedAdminTicket.customer_email}) · Created: {new Date(selectedAdminTicket.created_at).toLocaleString()}
                    {selectedAdminTicket.order_number && (
                      <span className="ms-2 badge bg-light text-dark border">
                        Linked Order: {selectedAdminTicket.order_number}
                      </span>
                    )}
                    {selectedAdminTicket.rfq_number && (
                      <span className="ms-2 badge bg-light text-dark border">
                        Linked RFQ: {selectedAdminTicket.rfq_number}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  type="button"
                  className="btn-close align-self-start"
                  onClick={() => setIsAdminTicketModalOpen(false)}
                ></button>
              </div>

              {/* Status Control Toolbar */}
              <div className="px-3 py-2 bg-light-subtle border-bottom d-flex align-items-center justify-content-between flex-wrap gap-2">
                <div className="d-flex align-items-center gap-2">
                  <span className="small fw-bold text-secondary">Set Status:</span>
                  <div className="btn-group btn-group-sm">
                    {['open', 'in_progress', 'resolved', 'closed'].map((st) => (
                      <button
                        key={st}
                        type="button"
                        disabled={updatingTicketStatus}
                        className={`btn btn-sm ${
                          selectedAdminTicket.status === st
                            ? 'btn-dark fw-bold'
                            : 'btn-outline-secondary bg-white'
                        }`}
                        onClick={() => handleAdminStatusChange(st)}
                      >
                        {st.replace('_', ' ').toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>
                <span className="small text-muted">
                  Last update: {new Date(selectedAdminTicket.updated_at).toLocaleTimeString()}
                </span>
              </div>

              {/* Body: Chronological Conversation */}
              <div className="modal-body p-3 p-md-4" style={{ maxHeight: '55vh', overflowY: 'auto' }}>
                <div className="d-flex flex-column gap-3 mb-4">
                  {selectedAdminTicket.messages.map((m) => {
                    const isAdmin = m.sender_role === 'admin';
                    return (
                      <div
                        key={m.id}
                        className={`d-flex flex-column ${isAdmin ? 'align-items-end' : 'align-items-start'}`}
                      >
                        <div className="small text-muted mb-1 px-1">
                          <strong>{isAdmin ? '🛡️ KPC Support Admin (You)' : `${selectedAdminTicket.customer_name} (Customer)`}</strong> ·{' '}
                          {new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })},{' '}
                          {new Date(m.created_at).toLocaleDateString()}
                        </div>
                        <div
                          className={`p-3 rounded-3 shadow-sm ${
                            isAdmin
                              ? 'bg-warning-subtle border border-warning text-dark'
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
                {selectedAdminTicket.attachments && selectedAdminTicket.attachments.length > 0 && (
                  <div className="border-top pt-3 mt-3">
                    <h6 className="small fw-bold text-dark mb-2">📎 Customer Attached Documents ({selectedAdminTicket.attachments.length}/2)</h6>
                    <div className="d-flex flex-wrap gap-2">
                      {selectedAdminTicket.attachments.map((att) => (
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
                                  ticketId: selectedAdminTicket.id,
                                  fileId: att.id,
                                  fileName: att.file_name,
                                  contentType: att.content_type,
                                })
                              }
                            >
                              👁 Inspect
                            </button>
                          )}
                          <a
                            href={`${API_BASE}/support/tickets/${selectedAdminTicket.id}/files/${att.id}?disposition=attachment`}
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

              {/* Footer: Admin Reply Box */}
              <div className="modal-footer border-top bg-light p-3">
                {selectedAdminTicket.status === 'resolved' || selectedAdminTicket.status === 'closed' ? (
                  <div className="alert alert-secondary py-2 mb-0 w-100 small text-center">
                    <strong>Notice:</strong> This ticket is currently marked as{' '}
                    <span className="badge bg-success">{selectedAdminTicket.status.toUpperCase()}</span>. To send further replies, set status back to Open or In Progress above.
                  </div>
                ) : (
                  <form onSubmit={handleSendAdminReply} className="w-100">
                    <div className="mb-2">
                      <textarea
                        rows={3}
                        className="form-control form-control-sm"
                        placeholder="Provide resolution details, technical feedback, or request additional information..."
                        value={adminReplyText}
                        onChange={(e) => setAdminReplyText(e.target.value)}
                        required
                        disabled={submittingAdminReply}
                      ></textarea>
                    </div>

                    <div className="d-flex justify-content-between align-items-center">
                      <span className="small text-muted">
                        Replying automatically marks an Open ticket as <strong>In Progress</strong>.
                      </span>
                      <div className="d-flex gap-2">
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => setIsAdminTicketModalOpen(false)}
                          disabled={submittingAdminReply}
                        >
                          Close
                        </button>
                        <button
                          type="submit"
                          className="btn btn-primary btn-sm fw-bold px-3"
                          disabled={submittingAdminReply || !adminReplyText.trim()}
                        >
                          {submittingAdminReply ? 'Sending Response...' : 'Send Admin Reply'}
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

      <PasswordChangeModal
        isOpen={isPasswordModalOpen}
        onClose={() => setIsPasswordModalOpen(false)}
      />
    </AdminLayout>
  );
}
