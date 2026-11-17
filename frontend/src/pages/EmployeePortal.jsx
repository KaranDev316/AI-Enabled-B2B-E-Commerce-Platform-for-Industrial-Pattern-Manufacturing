import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { PortalLayout } from '../components/PortalLayout';
import { PasswordChangeModal } from '../components/PasswordChangeModal';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export function EmployeePortal() {
  const { user, csrfToken } = useAuth();
  const [profile, setProfile] = useState(user?.employee_profile || {});
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({
    full_name: profile?.full_name || '',
    phone: profile?.phone || '',
  });

  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [feedback, setFeedback] = useState({ error: '', success: '' });

  function handleInputChange(e) {
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
        throw new Error(err?.detail?.message || 'Failed to update contact info.');
      }

      const updatedUser = await response.json();
      setProfile(updatedUser.employee_profile);
      setIsEditing(false);
      setFeedback({ error: '', success: 'Staff details updated successfully!' });
    } catch (err) {
      setFeedback({ error: err.message, success: '' });
    } finally {
      setSaveLoading(false);
    }
  }

  return (
    <PortalLayout
      title="Employee Workspace"
      subtitle="Shop Floor & Pattern Manufacturing Execution · Khodel Pattern Craft"
      roleBadgeColor="info text-dark"
    >
      {user?.must_change_password && (
        <div className="alert alert-warning border-warning shadow-sm rounded-3 mb-4 d-flex justify-content-between align-items-center">
          <div>
            <strong>Temporary Password Active:</strong> Your account was created with a temporary password by the Administrator. Please set your personal secure password now.
          </div>
          <button
            onClick={() => setIsPasswordModalOpen(true)}
            className="btn btn-warning btn-sm fw-bold ms-3"
          >
            Update Password
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

      <div className="row g-4">
        {/* Employee Info Card */}
        <div className="col-12 col-lg-5">
          <div className="card shadow-sm border-0 rounded-3 h-100">
            <div className="card-header bg-white border-bottom py-3 d-flex justify-content-between align-items-center">
              <h5 className="card-title h6 mb-0 fw-bold">Employee Record</h5>
              {!isEditing && (
                <button
                  onClick={() => {
                    setEditData({
                      full_name: profile?.full_name || '',
                      phone: profile?.phone || '',
                    });
                    setIsEditing(true);
                  }}
                  className="btn btn-outline-primary btn-sm"
                >
                  Edit Contact
                </button>
              )}
            </div>

            <div className="card-body">
              {isEditing ? (
                <form onSubmit={handleSaveProfile}>
                  <div className="mb-3">
                    <label className="form-label small fw-bold mb-1">Full Staff Name</label>
                    <input
                      name="full_name"
                      type="text"
                      className="form-control form-control-sm"
                      value={editData.full_name}
                      onChange={handleInputChange}
                      required
                    />
                  </div>

                  <div className="mb-4">
                    <label className="form-label small fw-bold mb-1">Phone Number</label>
                    <input
                      name="phone"
                      type="tel"
                      className="form-control form-control-sm"
                      value={editData.phone}
                      onChange={handleInputChange}
                    />
                  </div>

                  <div className="d-flex gap-2">
                    <button
                      type="submit"
                      className="btn btn-primary btn-sm fw-bold"
                      disabled={saveLoading}
                    >
                      {saveLoading ? 'Saving…' : 'Save Details'}
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
                  <p className="mb-1 text-secondary small">Staff Member</p>
                  <h6 className="fw-bold mb-3">{profile?.full_name || 'KPC Production Staff'}</h6>

                  <p className="mb-1 text-secondary small">Work Email</p>
                  <p className="mb-3">{user?.email}</p>

                  <p className="mb-1 text-secondary small">Phone Number</p>
                  <p className="mb-3">{profile?.phone || 'Not provided'}</p>

                  <p className="mb-1 text-secondary small">Department (Admin Assigned)</p>
                  <p className="mb-4">
                    <span className="badge bg-light text-dark border">
                      {profile?.department || 'Pattern Tooling & Machining'}
                    </span>
                  </p>

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

        {/* Manufacturing Execution Overview */}
        <div className="col-12 col-lg-7">
          <div className="card shadow-sm border-0 rounded-3 p-4">
            <h5 className="h6 fw-bold mb-3">Assigned Production Tasks (S10 / S12)</h5>
            <p className="text-secondary small mb-4">
              Employees inspect assigned jobs, view authorized pattern CAD drawings, log stage transitions
              (Design & Tooling → Machining/Production), and submit completed patterns for Admin Quality Review.
            </p>

            <div className="alert alert-light border rounded-3 p-3">
              <h6 className="fw-bold mb-1 small text-dark">Stage History & Rework Contract</h6>
              <p className="small text-muted mb-0">
                Every stage update is recorded in <code>job_stage_history</code> with actor timestamp.
                Quality check rejections by Admin require a rework note and reset progress to Machining.
              </p>
            </div>
          </div>
        </div>
      </div>

      <PasswordChangeModal
        isOpen={isPasswordModalOpen}
        onClose={() => setIsPasswordModalOpen(false)}
      />
    </PortalLayout>
  );
}
