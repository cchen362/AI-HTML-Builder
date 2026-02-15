import React, { useState, type FormEvent } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import './Auth.css';

type Tab = 'login' | 'register';

const LoginPage: React.FC = () => {
  const { login, register, error, clearError } = useAuth();
  const [tab, setTab] = useState<Tab>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const switchTab = (t: Tab) => {
    setTab(t);
    clearError();
    setUsername('');
    setPassword('');
    setDisplayName('');
    setInviteCode('');
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    try {
      if (tab === 'login') {
        await login(username, password);
      } else {
        await register(username, password, displayName || username, inviteCode);
      }
    } catch {
      // Error set in context
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-layout">
      {/* Background orbs */}
      <div className="auth-orb auth-orb--gold" />
      <div className="auth-orb auth-orb--mint" />
      <div className="auth-orb auth-orb--coral" />
      <div className="auth-orb auth-orb--purple" />
      <div className="auth-orb auth-orb--teal" />

      <div className="auth-center">
        {/* Branding */}
        <div className="auth-branding">
          <h1 className="auth-branding-title">AI HTML Builder</h1>
          <p className="auth-branding-subtitle">Create. Edit. Export.</p>

          <div className="auth-features">
            <div className="auth-feature">
              <span className="auth-feature-icon">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M10 0L12 7L20 10L12 13L10 20L8 13L0 10L8 7Z" fill="currentColor" />
                </svg>
              </span>
              <span className="auth-feature-text">AI-powered HTML generation from natural language</span>
            </div>
            <div className="auth-feature">
              <span className="auth-feature-icon">&lt;/&gt;</span>
              <span className="auth-feature-text">Zero-drift surgical editing via tool-use</span>
            </div>
            <div className="auth-feature">
              <span className="auth-feature-icon">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M10 3V13M10 13L6 9M10 13L14 9" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M4 15H16V17H4V15Z" fill="currentColor" />
                </svg>
              </span>
              <span className="auth-feature-text">Export to PDF, PNG, PPTX &amp; HTML</span>
            </div>
          </div>
        </div>

        {/* Form card */}
        <div className="auth-form-container">
          <div className="auth-tab-toggle">
            <button
              type="button"
              className={tab === 'login' ? 'active' : ''}
              onClick={() => switchTab('login')}
            >
              Sign In
            </button>
            <button
              type="button"
              className={tab === 'register' ? 'active' : ''}
              onClick={() => switchTab('register')}
            >
              Create Account
            </button>
          </div>

          {error && <div className="auth-error">{error}</div>}

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="auth-field">
              <label htmlFor="auth-username">Username</label>
              <input
                id="auth-username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                autoComplete="username"
                required
                autoFocus
              />
            </div>

            <div className="auth-field">
              <label htmlFor="auth-password">Password</label>
              <input
                id="auth-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
                required
              />
            </div>

            {tab === 'register' && (
              <>
                <div className="auth-field">
                  <label htmlFor="auth-display-name">Display Name</label>
                  <input
                    id="auth-display-name"
                    type="text"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="How others see you"
                    autoComplete="name"
                  />
                </div>

                <div className="auth-field">
                  <label htmlFor="auth-invite-code">Invite Code</label>
                  <input
                    id="auth-invite-code"
                    type="text"
                    value={inviteCode}
                    onChange={(e) => setInviteCode(e.target.value)}
                    placeholder="Ask your admin for a code"
                    required
                  />
                </div>
              </>
            )}

            <button
              type="submit"
              className="auth-submit"
              disabled={submitting || !username || !password || (tab === 'register' && !inviteCode)}
            >
              {submitting ? '...' : tab === 'login' ? 'Sign In' : 'Create Account'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
