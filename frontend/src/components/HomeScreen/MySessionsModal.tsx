import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../../services/api';
import ConfirmDialog from '../ConfirmDialog/ConfirmDialog';
import { relativeTime, daysUntilExpiry, expiryColor, groupSessionsByTime } from './sessionUtils';
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
  const [selectMode, setSelectMode] = useState(false);

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
      setSelectMode(false);
    }
  }, [isOpen, loadSessions]);

  // Escape key: inner dialogs → select mode → close modal
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (editingId) return;
        if (deleteTarget) return;
        if (bulkDeleteConfirm) return;
        if (selectMode) {
          setSelectMode(false);
          setSelectedIds(new Set());
          return;
        }
        onClose();
      }
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isOpen, onClose, editingId, deleteTarget, bulkDeleteConfirm, selectMode]);

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

  const groupedSessions = groupSessionsByTime(filteredSessions);

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
      setSelectMode(false);
    }
  }, [selectedIds]);

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

  // Track card index across groups for staggered animation
  let cardIndex = 0;

  return (
    <div
      className="sessions-overlay"
      onClick={(e) => { if (e.target === e.currentTarget && !bulkDeleting) onClose(); }}
    >
      <div className="sessions-panel">
        {/* Header */}
        <div className="sessions-header">
          <div className="sessions-header-left">
            {selectMode && sessions.length > 0 && (
              <label className="sessions-select-all" onClick={(e) => e.stopPropagation()}>
                <input
                  ref={selectAllRef}
                  type="checkbox"
                  className="sessions-checkbox"
                  checked={filteredSessions.length > 0 && filteredSessions.every(s => selectedIds.has(s.id))}
                  onChange={toggleSelectAll}
                />
              </label>
            )}
            <h2>
              My Sessions
              <span className="sessions-count">({sessions.length})</span>
            </h2>
          </div>
          <div className="sessions-header-right">
            {sessions.length > 0 && (
              <button
                type="button"
                className={`sessions-select-btn${selectMode ? ' sessions-select-btn--active' : ''}`}
                onClick={() => {
                  if (selectMode) {
                    setSelectedIds(new Set());
                  }
                  setSelectMode(!selectMode);
                }}
              >
                {selectMode ? 'Cancel' : 'Select'}
              </button>
            )}
            <button className="sessions-close" onClick={onClose} type="button">
              &times;
            </button>
          </div>
        </div>

        {/* Policy note */}
        <div className="sessions-policy">
          Sessions are automatically removed after 30 days of inactivity
        </div>

        {/* Search + filter count */}
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
          {filterText.trim() && (
            <span className="sessions-filter-count">
              {filteredSessions.length} of {sessions.length} sessions
            </span>
          )}
        </div>

        {/* Error */}
        {error && (
          <div className="sessions-error">{error}</div>
        )}

        {/* Card grid */}
        {loading && sessions.length === 0 ? (
          <div className="sessions-grid">
            <div className="sessions-loading">Loading...</div>
          </div>
        ) : sessions.length === 0 ? (
          <div className="sessions-grid">
            <div className="sessions-empty">No sessions yet</div>
          </div>
        ) : (
          <div className="sessions-grid">
            {filteredSessions.length === 0 ? (
              <div className="sessions-empty">No sessions match your filter</div>
            ) : (
              Array.from(groupedSessions.entries()).map(([group, groupSessions]) => (
                <React.Fragment key={group}>
                  <div className="session-group-header">{group}</div>
                  {groupSessions.map((session) => {
                    const daysLeft = daysUntilExpiry(session.last_active);
                    const isCurrent = session.id === currentSessionId;
                    const isEditing = editingId === session.id;
                    const docCount = session.doc_count - (session.infographic_count || 0);
                    const infraCount = session.infographic_count || 0;
                    const isEmpty = session.doc_count === 0;
                    const thisIndex = cardIndex++;

                    return (
                      <div
                        key={session.id}
                        className={
                          'session-card-modal' +
                          (isCurrent ? ' session-card-modal--current' : '') +
                          (selectedIds.has(session.id) ? ' session-card-modal--selected' : '') +
                          (isEmpty ? ' session-card-modal--empty' : '')
                        }
                        onClick={() => {
                          if (selectMode) {
                            toggleSelectOne(session.id);
                          } else if (!isEditing) {
                            onSelectSession(session.id);
                          }
                        }}
                        style={{ animationDelay: `${thisIndex * 40}ms` }}
                      >
                        {/* Select mode checkbox */}
                        {selectMode && (
                          <label className="session-card-modal-checkbox" onClick={(e) => e.stopPropagation()}>
                            <input
                              type="checkbox"
                              className="sessions-checkbox"
                              checked={selectedIds.has(session.id)}
                              onChange={() => toggleSelectOne(session.id)}
                            />
                          </label>
                        )}

                        {/* Hover actions */}
                        {!selectMode && (
                          <div className="session-card-modal-actions">
                            {!isEditing && (
                              <button
                                type="button"
                                className="session-action-btn"
                                onClick={(e) => { e.stopPropagation(); startRename(session); }}
                                title="Rename"
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
                              title="Delete"
                            >
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                              </svg>
                            </button>
                          </div>
                        )}

                        {/* Current badge */}
                        {isCurrent && <span className="session-card-modal-current">Current</span>}

                        {/* Title */}
                        <div className="session-card-modal-title">
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
                            <span onDoubleClick={(e) => { e.stopPropagation(); startRename(session); }}>
                              {session.title}
                            </span>
                          )}
                        </div>

                        {/* Subtitle (preview) — only if different from title */}
                        {session.first_message_preview &&
                         session.first_message_preview !== session.title && (
                          <div className="session-card-modal-subtitle">
                            {session.first_message_preview}
                          </div>
                        )}

                        {/* Doc type badges */}
                        <div className="session-card-modal-badges">
                          {docCount > 0 && (
                            <span className="session-card-modal-badge session-card-modal-badge--doc">
                              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm-1 2l5 5h-5V4zM6 20V4h5v7h7v9H6z"/>
                              </svg>
                              {docCount}
                            </span>
                          )}
                          {infraCount > 0 && (
                            <span className="session-card-modal-badge session-card-modal-badge--infographic">
                              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 22C6.49 22 2 17.51 2 12S6.49 2 12 2s10 4.04 10 9c0 3.31-2.69 6-6 6h-1.77c-.28 0-.5.22-.5.5 0 .12.05.23.13.33.41.47.64 1.06.64 1.67A2.5 2.5 0 0 1 12 22zm0-18c-4.41 0-8 3.59-8 8s3.59 8 8 8c.28 0 .5-.22.5-.5a.54.54 0 0 0-.14-.35c-.41-.46-.63-1.05-.63-1.65a2.5 2.5 0 0 1 2.5-2.5H16c2.21 0 4-1.79 4-4 0-3.86-3.59-7-8-7z"/>
                                <circle cx="6.5" cy="11.5" r="1.5"/>
                                <circle cx="9.5" cy="7.5" r="1.5"/>
                                <circle cx="14.5" cy="7.5" r="1.5"/>
                                <circle cx="17.5" cy="11.5" r="1.5"/>
                              </svg>
                              {infraCount}
                            </span>
                          )}
                          {isEmpty && <span className="session-card-modal-badge--empty">(empty)</span>}
                        </div>

                        {/* Footer: relative time + expiry */}
                        <div className="session-card-modal-footer">
                          <span>{relativeTime(session.last_active)}</span>
                          <span style={{ color: expiryColor(daysLeft) }}>
                            {daysLeft > 0 ? `${daysLeft}d left` : 'Expired'}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </React.Fragment>
              ))
            )}

            {/* Load more */}
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

        {/* Bulk bar (only in select mode with selections) */}
        {selectMode && selectedIds.size > 0 && (
          <div className="sessions-bulk-bar">
            <span className="sessions-bulk-count">
              {selectedIds.size} selected
            </span>
            <div className="sessions-bulk-actions">
              <button
                type="button"
                className="sessions-bulk-cancel"
                onClick={() => { setSelectMode(false); setSelectedIds(new Set()); }}
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
