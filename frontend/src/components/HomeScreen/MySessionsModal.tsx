import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../../services/api';
import ConfirmDialog from '../ConfirmDialog/ConfirmDialog';
import { relativeTime, daysUntilExpiry } from './sessionUtils';
import type { SessionSummary } from '../../types';
import './MySessionsModal.css';

interface MySessionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectSession: (sessionId: string) => void;
  currentSessionId: string | null;
}

function expiryColor(daysLeft: number): string {
  if (daysLeft > 14) return 'var(--signal-success)';
  if (daysLeft > 7) return 'var(--accent-primary)';
  return 'var(--signal-error)';
}

const PAGE_SIZE = 20;

const MySessionsModal: React.FC<MySessionsModalProps> = ({
  isOpen,
  onClose,
  onSelectSession,
  currentSessionId,
}) => {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<SessionSummary | null>(null);

  // Inline rename state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const editRef = useRef<HTMLInputElement>(null);

  const loadSessions = useCallback(async (offset: number = 0) => {
    setLoading(true);
    setError(null);
    try {
      const { sessions: data } = await api.listSessions(PAGE_SIZE, offset);
      if (offset === 0) {
        setSessions(data);
      } else {
        setSessions(prev => [...prev, ...data]);
      }
      setHasMore(data.length === PAGE_SIZE);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      loadSessions(0);
      setEditingId(null);
    }
  }, [isOpen, loadSessions]);

  // Escape key to close
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !editingId && !deleteTarget) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose, editingId, deleteTarget]);

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    try {
      await api.deleteSession(deleteTarget.id);
      setSessions(prev => prev.filter(s => s.id !== deleteTarget.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete session');
    }
    setDeleteTarget(null);
  }, [deleteTarget]);

  const handleLoadMore = useCallback(() => {
    loadSessions(sessions.length);
  }, [loadSessions, sessions.length]);

  // Inline rename
  const startRename = useCallback((session: SessionSummary) => {
    setEditingId(session.id);
    setEditValue(session.title);
    setTimeout(() => editRef.current?.focus(), 50);
  }, []);

  const saveRename = useCallback(async () => {
    if (!editingId || !editValue.trim()) {
      setEditingId(null);
      return;
    }
    try {
      await api.updateSessionTitle(editingId, editValue.trim());
      setSessions(prev =>
        prev.map(s => (s.id === editingId ? { ...s, title: editValue.trim() } : s))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rename session');
    }
    setEditingId(null);
  }, [editingId, editValue]);

  const cancelRename = useCallback(() => {
    setEditingId(null);
  }, []);

  if (!isOpen) return null;

  return (
    <div
      className="sessions-overlay"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="sessions-panel">
        <div className="sessions-header">
          <h2>My Sessions</h2>
          <button className="sessions-close" onClick={onClose} type="button">
            &times;
          </button>
        </div>

        <div className="sessions-policy">
          Sessions are automatically removed after 30 days of inactivity
        </div>

        {error && (
          <div className="sessions-error">{error}</div>
        )}

        {loading && sessions.length === 0 ? (
          <div className="sessions-loading">Loading...</div>
        ) : sessions.length === 0 ? (
          <div className="sessions-empty">No sessions yet</div>
        ) : (
          <div className="sessions-list">
            {sessions.map((session) => {
              const daysLeft = daysUntilExpiry(session.last_active);
              const isCurrent = session.id === currentSessionId;
              const isEditing = editingId === session.id;

              return (
                <div
                  key={session.id}
                  className={`session-row${isCurrent ? ' session-row--current' : ''}`}
                >
                  <div
                    className="session-row-info"
                    onClick={() => {
                      if (!isEditing) onSelectSession(session.id);
                    }}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !isEditing) onSelectSession(session.id);
                    }}
                  >
                    <div className="session-row-title-line">
                      {isEditing ? (
                        <input
                          ref={editRef}
                          className="session-rename-input"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') { e.preventDefault(); saveRename(); }
                            if (e.key === 'Escape') cancelRename();
                            e.stopPropagation();
                          }}
                          onClick={(e) => e.stopPropagation()}
                          onBlur={saveRename}
                          maxLength={200}
                        />
                      ) : (
                        <span
                          className="session-row-title"
                          onDoubleClick={(e) => { e.stopPropagation(); startRename(session); }}
                        >
                          {session.title}
                        </span>
                      )}
                      {isCurrent && <span className="session-current-badge">Current</span>}
                    </div>
                    <div className="session-row-meta">
                      <span>{session.doc_count} {session.doc_count === 1 ? 'doc' : 'docs'}</span>
                      <span className="session-row-dot">&middot;</span>
                      <span>{relativeTime(session.last_active)}</span>
                      <span className="session-row-dot">&middot;</span>
                      <span style={{ color: expiryColor(daysLeft) }}>
                        {daysLeft > 0 ? `${daysLeft}d left` : 'Expired'}
                      </span>
                    </div>
                  </div>

                  <div className="session-row-actions">
                    {!isEditing && (
                      <button
                        type="button"
                        className="session-action-btn"
                        onClick={(e) => { e.stopPropagation(); startRename(session); }}
                        title="Rename session"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                        </svg>
                      </button>
                    )}
                    <button
                      type="button"
                      className="session-action-btn session-action-btn--danger"
                      onClick={(e) => { e.stopPropagation(); setDeleteTarget(session); }}
                      title="Delete session"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                      </svg>
                    </button>
                  </div>
                </div>
              );
            })}

            {hasMore && (
              <button
                type="button"
                className="sessions-load-more"
                onClick={handleLoadMore}
                disabled={loading}
              >
                {loading ? 'Loading...' : 'Load more'}
              </button>
            )}
          </div>
        )}
      </div>

      <ConfirmDialog
        isOpen={!!deleteTarget}
        title="Delete Session?"
        message={`This will permanently delete "${deleteTarget?.title}" and all its documents.`}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
        confirmText="Delete"
        cancelText="Keep"
        danger
      />
    </div>
  );
};

export default MySessionsModal;
