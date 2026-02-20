import React, { useState, useEffect, useCallback } from 'react';
import { api, adminApi } from '../../services/api';
import type { User, BrandProfile } from '../../types';
import CostDashboard from './CostDashboard';
import './Auth.css';

type AdminTab = 'settings' | 'costs' | 'brands';

interface AdminPanelProps {
  isOpen: boolean;
  onClose: () => void;
  currentUserId: string;
}

const AdminPanel: React.FC<AdminPanelProps> = ({ isOpen, onClose, currentUserId }) => {
  const [activeTab, setActiveTab] = useState<AdminTab>('settings');
  const [users, setUsers] = useState<User[]>([]);
  const [inviteCode, setInviteCode] = useState('');
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Brand management state
  const [brands, setBrands] = useState<BrandProfile[]>([]);
  const [brandName, setBrandName] = useState('');
  const [brandSpec, setBrandSpec] = useState('');
  const [brandError, setBrandError] = useState<string | null>(null);
  const [brandSaving, setBrandSaving] = useState(false);

  const loadBrands = useCallback(async () => {
    try {
      const { brands: list } = await api.fetchBrands();
      setBrands(list);
    } catch {
      // silent
    }
  }, []);

  const handleCreateBrand = useCallback(async () => {
    const name = brandName.trim();
    const spec = brandSpec.trim();
    if (!name) { setBrandError('Brand name is required'); return; }
    if (!spec) { setBrandError('Brand spec is required'); return; }
    setBrandSaving(true);
    setBrandError(null);
    try {
      const brand = await adminApi.createBrand(name, spec);
      setBrands(prev => [...prev, brand]);
      setBrandName('');
      setBrandSpec('');
    } catch (err) {
      setBrandError(err instanceof Error ? err.message : 'Failed to create brand');
    } finally {
      setBrandSaving(false);
    }
  }, [brandName, brandSpec]);

  const handleDeleteBrand = useCallback(async (brandId: string) => {
    if (!confirm('Delete this brand profile? Users with this brand selected will revert to Default.')) return;
    try {
      await adminApi.deleteBrand(brandId);
      setBrands(prev => prev.filter(b => b.id !== brandId));
    } catch (err) {
      setBrandError(err instanceof Error ? err.message : 'Failed to delete brand');
    }
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [usersRes, codeRes] = await Promise.all([
        adminApi.getUsers(),
        adminApi.getInviteCode(),
      ]);
      setUsers(usersRes.users);
      setInviteCode(codeRes.invite_code);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load admin data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      setActiveTab('settings');
      loadData();
      loadBrands();
    }
  }, [isOpen, loadData, loadBrands]);

  const handleCopyCode = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(inviteCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: select text
    }
  }, [inviteCode]);

  const handleRegenerateCode = useCallback(async () => {
    try {
      const { invite_code } = await adminApi.regenerateInviteCode();
      setInviteCode(invite_code);
      setCopied(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to regenerate code');
    }
  }, []);

  const handleDeleteUser = useCallback(async (userId: string) => {
    try {
      await adminApi.deleteUser(userId);
      setUsers(prev => prev.filter(u => u.id !== userId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove user');
    }
  }, []);

  if (!isOpen) return null;

  return (
    <div className="admin-overlay" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="admin-panel">
        <div className="admin-header">
          <h2>Admin Panel</h2>
          <button className="admin-close" onClick={onClose} type="button">&times;</button>
        </div>

        <div className="admin-tab-bar">
          <button
            type="button"
            className={activeTab === 'settings' ? 'active' : ''}
            onClick={() => setActiveTab('settings')}
          >
            Settings
          </button>
          <button
            type="button"
            className={activeTab === 'costs' ? 'active' : ''}
            onClick={() => setActiveTab('costs')}
          >
            Costs
          </button>
          <button
            type="button"
            className={activeTab === 'brands' ? 'active' : ''}
            onClick={() => setActiveTab('brands')}
          >
            Brands
          </button>
        </div>

        {activeTab === 'settings' ? (
          <>
            {error && <div className="auth-error" style={{ margin: '1rem 1.5rem 0' }}>{error}</div>}

            {loading ? (
              <div className="admin-section" style={{ textAlign: 'center', color: 'var(--text-tertiary)' }}>
                Loading...
              </div>
            ) : (
              <>
                {/* Invite Code Section */}
                <div className="admin-section">
                  <h3 className="admin-section-title">Invite Code</h3>
                  <div className="invite-code-display">
                    <div className="invite-code-value">{inviteCode}</div>
                    <div className="invite-code-actions">
                      <button
                        type="button"
                        className={`admin-btn${copied ? ' admin-btn--copied' : ''}`}
                        onClick={handleCopyCode}
                      >
                        {copied ? 'Copied' : 'Copy'}
                      </button>
                      <button
                        type="button"
                        className="admin-btn"
                        onClick={handleRegenerateCode}
                      >
                        Regenerate
                      </button>
                    </div>
                  </div>
                </div>

                {/* User List Section */}
                <div className="admin-section">
                  <h3 className="admin-section-title">Users ({users.length})</h3>
                  <div className="admin-user-list">
                    {users.map((u) => (
                      <div key={u.id} className="admin-user-row">
                        <div className="admin-user-info">
                          <span className="admin-user-name">
                            {u.display_name}
                            {u.is_admin && <span className="admin-badge">Admin</span>}
                          </span>
                          <span className="admin-user-meta">@{u.username}</span>
                        </div>
                        <button
                          type="button"
                          className="admin-btn admin-btn--danger"
                          onClick={() => handleDeleteUser(u.id)}
                          disabled={u.id === currentUserId}
                          title={u.id === currentUserId ? 'Cannot remove yourself' : 'Remove user'}
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </>
        ) : activeTab === 'costs' ? (
          <CostDashboard isOpen={isOpen} />
        ) : (
          /* Brands tab */
          <div className="admin-section">
            <h3 className="admin-section-title">Brand Profiles</h3>
            {brandError && <div className="auth-error" style={{ marginBottom: '0.75rem' }}>{brandError}</div>}

            {brands.length === 0 ? (
              <div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--fs-sm)', marginBottom: '1rem' }}>
                No brand profiles yet. Add one below.
              </div>
            ) : (
              <div className="brand-list">
                {brands.map(b => (
                  <div key={b.id} className="brand-list-item">
                    <span className="brand-dot" style={{ backgroundColor: b.accent_color }} />
                    <span className="brand-list-name">{b.name}</span>
                    <button
                      type="button"
                      className="admin-btn admin-btn--danger"
                      onClick={() => handleDeleteBrand(b.id)}
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="brand-form">
              <h4 className="admin-section-title" style={{ fontSize: 'var(--fs-xs)' }}>Add Brand</h4>
              <input
                type="text"
                className="brand-name-input"
                placeholder="Brand name (max 50 chars)"
                value={brandName}
                onChange={e => setBrandName(e.target.value)}
                maxLength={50}
              />
              <textarea
                className="brand-spec-input"
                rows={8}
                placeholder={`Paste brand colors, fonts, and style guidelines. Example:\n\nCOLORS:\n- Primary: #006FCF (headers, CTAs)\n- Dark: #003478 (backgrounds, text)\n- Accent: #00A3A1 (highlights, charts)\n\nTYPOGRAPHY:\n- Headings: 'Helvetica Neue', sans-serif\n- Body: 'Inter', sans-serif\n\nTONE: Corporate-premium, data-forward, confident.`}
                value={brandSpec}
                onChange={e => setBrandSpec(e.target.value)}
                maxLength={5000}
              />
              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                <button
                  type="button"
                  className="admin-btn"
                  onClick={handleCreateBrand}
                  disabled={brandSaving}
                >
                  {brandSaving ? 'Saving...' : 'Save'}
                </button>
                <button
                  type="button"
                  className="admin-btn"
                  onClick={() => { setBrandName(''); setBrandSpec(''); setBrandError(null); }}
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPanel;
