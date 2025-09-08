import React, { useState } from 'react';
import './AdminLogin.css';

interface AdminLoginProps {
  onLogin: (token: string) => void;
  isLoading?: boolean;
}

const AdminLogin: React.FC<AdminLoginProps> = ({ onLogin, isLoading = false }) => {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const response = await fetch('/api/admin/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include', // Include cookies
        body: JSON.stringify({ password }),
      });

      // Check if response has content before parsing JSON
      const contentType = response.headers.get('content-type');
      let data;
      
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        // If not JSON, try to get text
        const text = await response.text();
        throw new Error(`Server error: ${text || response.statusText}`);
      }

      if (!response.ok) {
        throw new Error(data.detail || data.message || 'Login failed');
      }

      if (data.success) {
        onLogin(data.token);
      } else {
        setError(data.message || 'Login failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="admin-login-container">
        <div className="admin-login-form">
          <div className="loading">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-login-container">
      <div className="admin-login-form">
        <div className="admin-login-header">
          <h1>🔐 Admin Login</h1>
          <p>AI HTML Builder Analytics Dashboard</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="password">Admin Password</label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter admin password"
              required
              disabled={isSubmitting}
            />
          </div>

          {error && (
            <div className="error-message">
              ❌ {error}
            </div>
          )}

          <button 
            type="submit" 
            className="login-button"
            disabled={isSubmitting || !password.trim()}
          >
            {isSubmitting ? '🔄 Logging in...' : '🚀 Access Dashboard'}
          </button>
        </form>

        <div className="admin-info">
          <p>✨ Secure access to analytics, session tracking, and data export</p>
        </div>
      </div>
    </div>
  );
};

export default AdminLogin;