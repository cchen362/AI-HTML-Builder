import React, { useState, useEffect } from 'react';
import AdminLogin from '../components/AdminLogin/AdminLogin';
import AdminDashboard from '../components/AdminDashboard/AdminDashboard';

const AdminPage: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [authToken, setAuthToken] = useState<string>('');

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const response = await fetch('/api/admin/status', {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        if (data.authenticated) {
          setIsAuthenticated(true);
          setAuthToken('authenticated'); // Token is in HTTP-only cookie
        }
      }
    } catch (error) {
      console.error('Auth status check failed:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogin = (token: string) => {
    setAuthToken(token);
    setIsAuthenticated(true);
  };

  const handleLogout = async () => {
    try {
      await fetch('/api/admin/logout', {
        method: 'POST',
        credentials: 'include'
      });
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      setIsAuthenticated(false);
      setAuthToken('');
    }
  };

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #f8f9fa 0%, #e3f2fd 100%)',
        fontFamily: 'Inter, sans-serif'
      }}>
        <div style={{
          textAlign: 'center',
          color: '#003366'
        }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔄</div>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {isAuthenticated ? (
        <AdminDashboard onLogout={handleLogout} />
      ) : (
        <AdminLogin onLogin={handleLogin} />
      )}
    </>
  );
};

export default AdminPage;