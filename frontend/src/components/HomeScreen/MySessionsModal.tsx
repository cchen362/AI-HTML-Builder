import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../../services/api';
import ConfirmDialog from '../ConfirmDialog/ConfirmDialog';
import { relativeTime, daysUntilExpiry, expiryColor } from './sessionUtils';
import type { SessionSummary } from '../../types';
import './MySessionsModal.css';

interface MySessionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectSession: (sessionId: string) => void;
  currentSessionId: string | null;
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
  const [filterText, setFilterText] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleteConfirm, setBulkDeleteConfirm] = useState(false);
  const [bulkDeleting, setBulkDeleting] = useState(false);

  // Inline rename state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const editRef = useRef<HTMLInputElement>(null);
  const selectAllRef = useRef<HTMLInputElement>(null);

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
      setFilterText('');
      setSelectedIds(new Set());
      setBulkDeleteConfirm(false);
    }
  }, [isOpen, loadSessions]);

  // Escape key to close (priority: inner dialogs → selections → close modal)
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (editingId) return;
        if (deleteTarget) return;
        if (bulkDeleteConfirm) return;
        if (selectedIds.size > 0) {
          setSelectedIds(new Set());
          return;
        }
        onClose();
      }
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose, editingId, deleteTarget, bulkDeleteConfirm, selectedIds]);

  const handleDelete = useCallback(async () => {
    if (!deleteTarget) return;
    try {
      await api.deleteSession(deleteTarget.id);
      setSessions(prev => prev.filter(s => s.id !== deleteTarget.id));
      setSelectedIds(prev => {
        if (prev.has(deleteTarget.id)) {
          const next = new Set(prev);
          next.delete(deleteTarget.id);
          return next;
        }
        return prev;
      });
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

  // Bulk select handlers
  const toggleSelectOne = useCallback((id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const filteredSessions = filterText.trim()
    ? sessions.filter(s =>
        s.title.toLowerCase().includes(filterText.toLowerCase()) ||
        s.first_message_preview.toLowerCase().includes(filterText.toLowerCase())
      )
    : sessions;

  const toggleSelectAll = useCallback(() => {
    const visibleIds = filteredSessions.map(s => s.id);
    const allSelected = visibleIds.length > 0 && visibleIds.every(id => selectedIds.has(id));
    if (allSelected) {
      setSelectedIds(prev => {
        const next = new Set(prev);
        visibleIds.forEach(id => next.delete(id));
        return next;
      });
    } else {
      setSelectedIds(prev => {
        const next = new Set(prev);
        visibleIds.forEach(id => next.add(id));
        return next;
      });
    }
  }, [filteredSessions, selectedIds]);

  const handleBulkDelete = useCallback(async () => {
    setBulkDeleting(true);
    try {
      const idsToDelete = [...selectedIds];
      for (const id of idsToDelete) {
        try {
          await api.deleteSession(id);
        } catch {
          // Continue deleting remaining sessions even if one fails
        }
      }
      setSessions(prev => prev.filter(s => !selectedIds.has(s.id)));
      setSelectedIds(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete sessions');
    } finally {
      setBulkDeleting(false);
      setBulkDeleteConfirm(false);
    }
  }, [selectedIds]);

  const cancelBulkSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  // Sync select-all checkbox indeterminate state
  useEffect(() => {
    if (!selectAllRef.current) return;
    const visibleCount = filteredSessions.length;
    const selectedVisible = filteredSessions.filter(s => selectedIds.has(s.id)).length;
    selectAllRef.current.indeterminate = selectedVisible > 0 && selectedVisible < visibleCount;
  }, [filteredSessions, selectedIds]);

  // Clear selections for sessions no longer visible after filter change
  useEffect(() => {
    if (filterText.trim() && selectedIds.size > 0) {
      const visibleIds = new Set(filteredSessions.map(s => s.id));
      const hasInvisibleSelected = [...selectedIds].some(id => !visibleIds.has(id));
      if (hasInvisibleSelected) {
        setSelectedIds(prev => {
          const next = new Set<string>();
          prev.forEach(id => {
            if (visibleIds.has(id)) next.add(id);
          });
          return next;
        });
      }
    }
  }, [filterText, filteredSessions, selectedIds]);

  if (!isOpen) return null;

  return (
    <div
      className="sessions-overlay"
      onClick={(e) => { if (e.target === e.currentTarget && !bulkDeleting) onClose(); }}
    >
      <div className="sessions-panel">
        <div className="sessions-header">
          <div className="sessions-header-left">
            {sessions.length > 0 && (
              <label className="sessions-select-all">
                <input
                  ref={selectAllRef}
                  type="checkbox"
                  className="session-row-checkbox"
                  checked={filteredSessions.length > 0 && filteredSessions.every(s => selectedIds.has(s.id))}
                  onChange={toggleSelectAll}
                />
              </label>
            )}
            <h2>My Sessions</h2>
          </div>
          <button className="sessions-close" onClick={onClose} type="button">
            &times;
          </button>
        </div>

        <div className="sessions-policy">
          Sessions are automatically removed after 30 days of inactivity
        </div>

        <div className="sessions-search">
          <svg className="sessions-search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            className="sessions-search-input"
            placeholder="Filter sessions..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
          />
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
            {filteredSessions.length === 0 ? (
              <div className="sessions-empty">No sessions match your filter</div>
            ) : filteredSessions.map((session) => {
              const daysLeft = daysUntilExpiry(session.last_active);
              const isCurrent = session.id === currentSessionId;
              const isEditing = editingId === session.id;

              return (
                <div
                  key={session.id}
                  className={`session-row${isCurrent ? ' session-row--current' : ''}${selectedIds.has(session.id) ? ' session-row--selected' : ''}`}
                >
                  <label className="session-row-checkbox-label" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      className="session-row-checkbox"
                      checked={selectedIds.has(session.id)}
                      onChange={() => toggleSelectOne(session.id)}
                    />
                  </label>

                  <div className="session-row-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                      <line x1="16" y1="13" x2="8" y2="13"/>
                      <line x1="16" y1="17" x2="8" y2="17"/>
                      <line x1="10" y1="9" x2="8" y2="9"/>
                    </svg>
                  </div>

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
                      <span className="session-doc-badge">
                        {session.doc_count} {session.doc_count === 1 ? 'doc' : 'docs'}
                      </span>
                    </div>
                    <div className="session-row-meta">
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

            {hasMore && !filterText.trim() && (
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

        {selectedIds.size > 0 && (
          <div className="sessions-bulk-bar">
            <span className="sessions-bulk-count">
              {selectedIds.size} selected
            </span>
            <div className="sessions-bulk-actions">
              <button
                type="button"
                className="sessions-bulk-cancel"
                onClick={cancelBulkSelection}
              >
                Cancel
              </button>
              <button
                type="button"
                className="sessions-bulk-delete"
                onClick={() => setBulkDeleteConfirm(true)}
                disabled={bulkDeleting}
              >
                {bulkDeleting ? 'Deleting...' : `Delete ${selectedIds.size} Session${selectedIds.size === 1 ? '' : 's'}`}
              </button>
            </div>
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

      <ConfirmDialog
        isOpen={bulkDeleteConfirm}
        title={`Delete ${selectedIds.size} Session${selectedIds.size === 1 ? '' : 's'}?`}
        message={`This will permanently delete ${selectedIds.size} session${selectedIds.size === 1 ? '' : 's'} and all their documents. This cannot be undone.`}
        onConfirm={handleBulkDelete}
        onCancel={() => setBulkDeleteConfirm(false)}
        confirmText={`Delete ${selectedIds.size}`}
        cancelText="Keep"
        danger
      />
    </div>
  );
};

export default MySessionsModal;
