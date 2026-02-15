import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi } from '../services/api';
import type { User } from '../types';

interface AuthState {
  user: User | null;
  isLoading: boolean;
  needsSetup: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, displayName: string, inviteCode: string) => Promise<void>;
  setup: (username: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [needsSetup, setNeedsSetup] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check auth state on mount
  useEffect(() => {
    let cancelled = false;

    async function checkAuth() {
      try {
        // First check if setup is needed
        const { needs_setup } = await authApi.needsSetup();
        if (cancelled) return;

        if (needs_setup) {
          setNeedsSetup(true);
          setIsLoading(false);
          return;
        }

        // Try to get current user from cookie
        try {
          const { user: me } = await authApi.getMe();
          if (!cancelled) setUser(me);
        } catch {
          // Not logged in — that's fine
        }
      } catch {
        // Server unreachable or error — show login
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    checkAuth();
    return () => { cancelled = true; };
  }, []);

  // Listen for 401 events from api.ts
  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
    };
    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', handleUnauthorized);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    setError(null);
    try {
      const { user: loggedIn } = await authApi.login(username, password);
      setUser(loggedIn);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Login failed';
      setError(msg.includes('401') ? 'Invalid username or password' : msg);
      throw err;
    }
  }, []);

  const register = useCallback(async (username: string, password: string, displayName: string, inviteCode: string) => {
    setError(null);
    try {
      const { user: registered } = await authApi.register(username, password, displayName, inviteCode);
      setUser(registered);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Registration failed';
      if (msg.includes('400')) setError('Invalid invite code');
      else if (msg.includes('409')) setError('Username already taken');
      else setError(msg);
      throw err;
    }
  }, []);

  const setup = useCallback(async (username: string, password: string, displayName: string) => {
    setError(null);
    try {
      const { user: admin } = await authApi.setup(username, password, displayName);
      setUser(admin);
      setNeedsSetup(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Setup failed';
      setError(msg);
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore — clear state anyway
    }
    setUser(null);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return (
    <AuthContext.Provider value={{ user, isLoading, needsSetup, error, login, register, setup, logout, clearError }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
