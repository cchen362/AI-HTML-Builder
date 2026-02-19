import React, { useState, useEffect, useCallback } from 'react';
import { adminApi } from '../../services/api';
import type { User } from '../../types';
import CostDashboard from './CostDashboard';
import './Auth.css';

type AdminTab = 'settings' | 'costs';

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
    }
  }, [isOpen, loadData]);

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
        ) : (
          <CostDashboard isOpen={isOpen} />
        )}
      </div>
    </div>
  );
};

export default AdminPanel;
