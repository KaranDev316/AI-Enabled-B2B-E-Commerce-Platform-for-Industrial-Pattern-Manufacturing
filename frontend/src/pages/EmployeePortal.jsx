import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { EmployeeLayout, EmployeeIcon as Icon, employeePages } from '../components/EmployeeLayout';
import { EmployeeDashboard, EmployeeTasks, EmployeeIssue } from '../components/EmployeeWork';
import { PasswordChangeModal } from '../components/PasswordChangeModal';
import { useKpcLiveSync, emitKpcSync, LiveSyncBadge } from '../utils/kpcLiveSync';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export function EmployeePortal() {
  const { user, csrfToken } = useAuth();
  const [activeTab, setActiveTab] = useState(() => { const tab = new URLSearchParams(window.location.search).get('tab'); return employeePages.some(page => page.id === tab) ? tab : 'dashboard'; });
  function navigateTab(tab) {
    setActiveTab(tab); setFeedback({ error: '', success: '' });
    const url = new URL(window.location.href); url.searchParams.set('tab', tab);
    window.history.replaceState(null, '', url); window.scrollTo(0, 0);
  }
  const [profile, setProfile] = useState(user?.employee_profile || {});
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({
    full_name: profile?.full_name || '',
    phone: profile?.phone || '',
  });

  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [feedback, setFeedback] = useState({ error: '', success: '' });

  const { isLiveSynced } = useKpcLiveSync(() => {
    // Silent background sync
  }, 4000);

  function handleInputChange(e) {
    const { name, value } = e.target;
    setEditData((prev) => ({ ...prev, [name]: value }));
  }

  async function handleSaveProfile(e) {
    e.preventDefault();
    setFeedback({ error: '', success: '' });
    if (saveLoading) return;
    if (editData.full_name.trim().length < 2) { setFeedback({ error: 'Enter your full name using at least 2 characters.', success: '' }); return; }
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
      setFeedback({ error: '', success: 'Your profile has been updated.' });
      emitKpcSync('PROFILE_UPDATED');
    } catch (err) {
      setFeedback({ error: err.message, success: '' });
    } finally {
      setSaveLoading(false);
    }
  }

  function startEditing() {
    setEditData({ full_name: profile.full_name || '', phone: profile.phone || '' });
    setIsEditing(true);
  }

  const initials = (profile.full_name || 'Employee').split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase();
  return <EmployeeLayout activeTab={activeTab} onNavigate={navigateTab} profile={profile}>
    {user.must_change_password && <div className="alert alert-warning employee-password-notice" role="alert"><div><strong>Update your temporary password</strong><p>Your Administrator created this account. Set your own password to secure it.</p></div><button className="btn btn-primary" onClick={() => setIsPasswordModalOpen(true)}>Update Password</button></div>}
    {feedback.success && <div className="alert alert-success alert-dismissible" role="status">{feedback.success}<button className="btn-close" aria-label="Dismiss success message" onClick={() => setFeedback({ ...feedback, success: '' })}/></div>}
    {feedback.error && <div className="alert alert-danger alert-dismissible" role="alert">{feedback.error}<button className="btn-close" aria-label="Dismiss error message" onClick={() => setFeedback({ ...feedback, error: '' })}/></div>}
    {activeTab === 'dashboard' && <EmployeeDashboard onNavigate={navigateTab}/>}
    {activeTab === 'tasks' && <EmployeeTasks/>}
    {activeTab === 'completed' && <EmployeeTasks completed/>}
    {activeTab === 'issue' && <EmployeeIssue/>}
    {activeTab === 'profile' && <>
      <div className="employee-profile-toolbar">{!isEditing && <button className="btn btn-outline-primary" onClick={startEditing}><Icon name="profile" size={18}/> Edit Profile</button>}</div>
      <div className="employee-profile-grid"><section className="card employee-personal-card"><div className="employee-profile-identity"><span className="employee-avatar large">{initials}</span><div><h2>{profile.full_name || 'Employee'}</h2><p>{profile.department || 'Department not assigned'}</p><span className="employee-active-badge">{user.is_active ? 'Active' : 'Inactive'}</span></div></div><div className="employee-personal-body"><h3>Personal Information</h3><form onSubmit={handleSaveProfile}><div className="employee-form-grid"><label>Full Name{isEditing && <span className="customer-required"> *</span>}<input className="form-control" name="full_name" autoComplete="name" value={isEditing ? editData.full_name : profile.full_name || ''} onChange={handleInputChange} readOnly={!isEditing} required minLength={2} maxLength={255} disabled={saveLoading}/></label><label>Employee ID<input className="form-control" value={String(user.id)} readOnly/></label><label className="employee-field-wide">Email<input className="form-control" type="email" value={user.email} readOnly/></label><label className="employee-field-wide">Phone<input className="form-control" type="tel" name="phone" autoComplete="tel" value={isEditing ? editData.phone : profile.phone || ''} onChange={handleInputChange} readOnly={!isEditing} maxLength={50} placeholder="Not provided" disabled={saveLoading}/></label></div>{isEditing && <div className="employee-profile-actions"><button className="btn btn-outline-primary" type="button" onClick={() => setIsEditing(false)} disabled={saveLoading}>Cancel</button><button className="btn btn-primary" type="submit" disabled={saveLoading}>{saveLoading ? 'Saving…' : 'Save Changes'}</button></div>}</form></div></section>
      <div className="employee-profile-side"><section className="card"><div className="customer-section-header"><h2><Icon name="company"/> Employment Details</h2></div><div className="employee-employment"><dl><div><dt>Department</dt><dd>{profile.department || 'Not assigned'}</dd></div><div><dt>Account role</dt><dd>Employee</dd></div></dl><p>Employment details are assigned by your Administrator.</p></div></section><section className="card"><div className="customer-section-header"><h2><Icon name="lock"/> Account & Security</h2></div><div className="employee-security"><div><h3>Password</h3><p>Changing your password signs you out of existing sessions.</p></div><button className="btn btn-outline-primary" onClick={() => setIsPasswordModalOpen(true)}>Change Password</button></div></section></div></div>
    </>}
    <PasswordChangeModal isOpen={isPasswordModalOpen} onClose={() => setIsPasswordModalOpen(false)}/>
    <LiveSyncBadge visible={isLiveSynced} />
  </EmployeeLayout>;
}
