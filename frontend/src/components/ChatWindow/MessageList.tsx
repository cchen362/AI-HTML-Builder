import React, { useEffect, useRef } from 'react';
import type { ChatMessage, Document, SessionSummary } from '../../types';
import type { PromptTemplate } from '../../data/promptTemplates';
import StreamingMarkdown from '../Chat/StreamingMarkdown';
import TemplateCards from '../EmptyState/TemplateCards';
import SessionCard from '../HomeScreen/SessionCard';
import '../HomeScreen/HomeScreen.css';
import './MessageList.css';

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming?: boolean;
  streamingContent?: string;
  onSelectTemplate?: (template: PromptTemplate) => void;
  documents?: Document[];
  showHomeScreen?: boolean;
  recentSessions?: SessionSummary[];
  onSelectSession?: (sessionId: string) => void;
  onViewAllSessions?: () => void;
  displayName?: string;
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  isStreaming = false,
  streamingContent = '',
  onSelectTemplate,
  documents = [],
  showHomeScreen,
  recentSessions,
  onSelectSession,
  onViewAllSessions,
  displayName,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const docNameMap = documents.length > 1
    ? new Map(documents.map(d => [d.id, d.title]))
    : null;

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent]);

  const formatTimestamp = (created_at: string) => {
    return new Date(created_at).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const showTemplates = messages.length === 0 && !isStreaming && onSelectTemplate;

  return (
    <div className="message-list">
      {showTemplates && (
        <div className="home-content">
          {displayName && (
            <h1 className="home-welcome">Welcome back, {displayName}</h1>
          )}
          {showHomeScreen && recentSessions && recentSessions.length > 0 && (
            <section className="home-section home-zone home-zone--sessions">
              <h2 className="home-section-heading home-section-heading--sessions">
                Continue a session
              </h2>
              <div className="home-sessions-row">
                {recentSessions.map((session, i) => (
                  <SessionCard
                    key={session.id}
                    session={session}
                    onClick={() => onSelectSession?.(session.id)}
                    style={{ animationDelay: `${i * 80}ms` }}
                  />
                ))}
              </div>
              <button
                type="button"
                className="home-view-all"
                onClick={onViewAllSessions}
              >
                View all sessions &rarr;
              </button>
            </section>
          )}
          <section className="home-section home-zone home-zone--templates">
            <h2 className="home-section-heading home-section-heading--templates">
              Start with a template
            </h2>
            <TemplateCards onSelectTemplate={onSelectTemplate} />
          </section>
          <div className="home-prompt-bridge">
            <span className="home-prompt-bridge-line" />
            <span className="home-prompt-bridge-label">or just describe what you need</span>
            <span className="home-prompt-bridge-line" />
          </div>
        </div>
      )}

      {messages.map((message) => (
        <div
          key={message.id}
          className={`message ${message.role === 'user' ? 'message-user' : 'message-ai'}`}
        >
          <div className="message-header">
            <span className="message-sender">
              {message.role === 'user' ? 'You' : 'BUILDER'}
            </span>
            <span className="message-meta">
              {docNameMap && message.document_id && docNameMap.has(message.document_id) && (
                <span className="message-doc-badge">{docNameMap.get(message.document_id)}</span>
              )}
              <span className="message-timestamp">
                {formatTimestamp(message.created_at)}
              </span>
            </span>
          </div>
          <div className="message-content">
            {message.role === 'assistant' ? (
              <StreamingMarkdown content={message.content} />
            ) : message.templateName ? (
              <div className="message-template-display">
                <div className="message-template-badge">
                  <span className="message-template-icon">&#x1F4CB;</span>
                  <span className="message-template-name">{message.templateName}</span>
                </div>
                {message.userContent && message.userContent !== '(template only)' && (
                  <div className="message-user-content">{message.userContent}</div>
                )}
              </div>
            ) : (
              message.content
            )}
          </div>
        </div>
      ))}

      {isStreaming && (
        <div className="message message-ai processing">
          <div className="message-header">
            <span className="message-sender">BUILDER</span>
          </div>
          <div className="message-content">
            {streamingContent ? (
              <StreamingMarkdown content={streamingContent} isStreaming />
            ) : (
              <>
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                Generating...
              </>
            )}
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList;
