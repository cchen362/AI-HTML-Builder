import React, { useState, useCallback, useEffect, useRef } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import type { ChatMessage, Document, User, SessionSummary } from '../../types';
import type { PromptTemplate } from '../../data/promptTemplates';

import './ChatWindow.css';

function getInitials(name: string): string {
  const words = name.trim().split(/\s+/);
  if (words.length >= 2) return (words[0][0] + words[words.length - 1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

interface ChatWindowProps {
  messages: ChatMessage[];
  onSendMessage: (message: string, files?: File[], templateName?: string, userContent?: string, brandId?: string) => void;
  isStreaming?: boolean;
  streamingContent?: string;
  error?: string | null;
  onDismissError?: () => void;
  onCancelRequest?: () => void;
  sessionId?: string | null;
  onStartNewSession?: () => void;
  documents?: Document[];
  user?: User;
  onAdminSettings?: () => void;
  onLogout?: () => void;
  onOpenMySessions?: () => void;
  showHomeScreen?: boolean;
  recentSessions?: SessionSummary[];
  onSelectSession?: (sessionId: string) => void;
  onViewAllSessions?: () => void;
  sessionTitle?: string;
  onRenameSession?: (title: string) => void;
}

const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  onSendMessage,
  isStreaming = false,
  streamingContent = '',
  error = null,
  onDismissError,
  onCancelRequest,
  sessionId,
  onStartNewSession,
  documents = [],
  user,
  onAdminSettings,
  onLogout,
  onOpenMySessions,
  showHomeScreen,
  recentSessions,
  onSelectSession,
  onViewAllSessions,
  sessionTitle,
  onRenameSession,
}) => {
  const [pendingTemplate, setPendingTemplate] = useState<PromptTemplate | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editTitleValue, setEditTitleValue] = useState('');
  const menuRef = useRef<HTMLDivElement>(null);

  const handleSelectTemplate = useCallback((template: PromptTemplate) => {
    setPendingTemplate(template);
  }, []);

  const handleTemplateClaimed = useCallback(() => {
    setPendingTemplate(null);
  }, []);

  useEffect(() => {
    if (!menuOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    const timer = setTimeout(() => {
      document.addEventListener('click', handleClickOutside);
    }, 0);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('click', handleClickOutside);
    };
  }, [menuOpen]);

  return (
    <div className="chat-window">
      <div className="chat-header">
        <h2>AI HTML Builder</h2>
        <div className="header-right-group">
          {sessionTitle && !showHomeScreen && (
            isEditingTitle ? (
              <input
                className="header-session-input"
                value={editTitleValue}
                onChange={(e) => setEditTitleValue(e.target.value)}
                onBlur={() => {
                  if (editTitleValue.trim() && editTitleValue.trim() !== sessionTitle) {
                    onRenameSession?.(editTitleValue.trim());
                  }
                  setIsEditingTitle(false);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    (e.target as HTMLInputElement).blur();
                  }
                  if (e.key === 'Escape') {
                    setIsEditingTitle(false);
                  }
                }}
                maxLength={200}
                autoFocus
              />
            ) : (
              <button
                type="button"
                className="header-session-title"
                onClick={() => {
                  setEditTitleValue(sessionTitle);
                  setIsEditingTitle(true);
                }}
                title="Click to rename session"
              >
                {sessionTitle}
                <svg className="header-title-pencil" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M17 3a2.85 2.85 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
              </button>
            )
          )}
          <div className="header-menu-wrapper" ref={menuRef}>
            <button
              className={`header-avatar-btn${menuOpen ? ' active' : ''}`}
              onClick={() => setMenuOpen(!menuOpen)}
              aria-label="Account menu"
              title={user ? `Signed in as ${user.display_name}` : ''}
              type="button"
            >
              {getInitials(user?.display_name || '?')}
            </button>
            {menuOpen && (
              <div className="header-menu-dropdown">
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    onStartNewSession?.();
                  }}
                  disabled={isStreaming}
                >
                  <svg className="menu-item-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><path d="M12 8v8M8 12h8"/></svg>
                  New Session
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    onOpenMySessions?.();
                  }}
                >
                  <svg className="menu-item-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                  My Sessions
                </button>
                <div className="menu-divider" />
                {user?.is_admin && (
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpen(false);
                      onAdminSettings?.();
                    }}
                  >
                    <svg className="menu-item-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                    Admin Settings
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    onLogout?.();
                  }}
                >
                  <svg className="menu-item-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                  Logout
                </button>
                <div className="session-id-display">
                  Session: {sessionId?.slice(0, 8) || '—'}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span className="error-text">{error}</span>
          <button onClick={onDismissError} className="error-dismiss">&times;</button>
        </div>
      )}

      <MessageList
        messages={messages}
        isStreaming={isStreaming}
        streamingContent={streamingContent}
        onSelectTemplate={handleSelectTemplate}
        documents={documents}
        showHomeScreen={showHomeScreen}
        recentSessions={recentSessions}
        onSelectSession={onSelectSession}
        onViewAllSessions={onViewAllSessions}
        displayName={user?.display_name}
      />

      <ChatInput
        onSendMessage={onSendMessage}
        isProcessing={isStreaming}
        placeholder="Describe the HTML you want to create, or browse templates for inspiration..."
        externalTemplate={pendingTemplate}
        onExternalTemplateClaimed={handleTemplateClaimed}
        onCancelRequest={onCancelRequest}
      />
    </div>
  );
};

export default ChatWindow;
