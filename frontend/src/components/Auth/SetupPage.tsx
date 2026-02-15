import React, { useState, type FormEvent } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import './Auth.css';

const SetupPage: React.FC = () => {
  const { setup, error, clearError } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    clearError();
    setSubmitting(true);
    try {
      await setup(username, password, displayName || username);
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
          <h1 className="auth-branding-title">Welcome to AI HTML Builder</h1>
          <p className="auth-branding-subtitle">First-time setup</p>

          <div className="auth-features">
            <div className="auth-feature">
              <span className="auth-feature-icon">1.</span>
              <span className="auth-feature-text">Create your admin account below</span>
            </div>
            <div className="auth-feature">
              <span className="auth-feature-icon">2.</span>
              <span className="auth-feature-text">Share invite codes with your team</span>
            </div>
            <div className="auth-feature">
              <span className="auth-feature-icon">3.</span>
              <span className="auth-feature-text">Start building beautiful HTML pages</span>
            </div>
          </div>
        </div>

        {/* Form card */}
        <div className="auth-form-container">
          <div className="auth-setup-welcome">
            <h2>Create Admin Account</h2>
            <p>This will be the first user with full administrative access. You can invite others after setup.</p>
          </div>

          {error && <div className="auth-error">{error}</div>}

          <form className="auth-form" onSubmit={handleSubmit}>
            <div className="auth-field">
              <label htmlFor="setup-username">Username</label>
              <input
                id="setup-username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Choose a username"
                autoComplete="username"
                required
                autoFocus
              />
            </div>

            <div className="auth-field">
              <label htmlFor="setup-password">Password</label>
              <input
                id="setup-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Choose a password"
                autoComplete="new-password"
                required
              />
            </div>

            <div className="auth-field">
              <label htmlFor="setup-display-name">Display Name</label>
              <input
                id="setup-display-name"
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="How others see you (optional)"
                autoComplete="name"
              />
            </div>

            <button
              type="submit"
              className="auth-submit"
              disabled={submitting || !username || !password}
            >
              {submitting ? '...' : 'Create Admin Account'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default SetupPage;
