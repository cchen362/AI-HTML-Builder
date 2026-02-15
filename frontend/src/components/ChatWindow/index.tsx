import React, { useState, useCallback, useEffect, useRef } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import type { ChatMessage, Document, User } from '../../types';
import type { PromptTemplate } from '../../data/promptTemplates';

import './ChatWindow.css';

interface ChatWindowProps {
  messages: ChatMessage[];
  onSendMessage: (message: string, files?: File[], templateName?: string, userContent?: string) => void;
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
}) => {
  const [pendingTemplate, setPendingTemplate] = useState<PromptTemplate | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
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
        <div className="header-menu-wrapper" ref={menuRef}>
          <button
            className={`header-menu-btn${menuOpen ? ' active' : ''}`}
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Session menu"
            type="button"
          >
            ⋮
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
                New Session
              </button>
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false);
                  onOpenMySessions?.();
                }}
              >
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
                Logout
              </button>
              <div className="session-id-display">
                {user ? `Signed in as ${user.display_name}` : ''}
              </div>
              <div className="session-id-display">
                Session: {sessionId?.slice(0, 8) || '—'}
              </div>
            </div>
          )}
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
