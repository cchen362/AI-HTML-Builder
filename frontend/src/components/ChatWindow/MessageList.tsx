import React, { useEffect, useRef } from 'react';
import type { ChatMessage, Document } from '../../types';
import type { PromptTemplate } from '../../data/promptTemplates';
import StreamingMarkdown from '../Chat/StreamingMarkdown';
import TemplateCards from '../EmptyState/TemplateCards';
import './MessageList.css';

interface MessageListProps {
  messages: ChatMessage[];
  isStreaming?: boolean;
  streamingContent?: string;
  onSelectTemplate?: (template: PromptTemplate) => void;
  documents?: Document[];
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  isStreaming = false,
  streamingContent = '',
  onSelectTemplate,
  documents = [],
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
        <TemplateCards
          onSelectTemplate={onSelectTemplate}
        />
      )}

      {messages.map((message) => (
        <div
          key={message.id}
          className={`message ${message.role === 'user' ? 'message-user' : 'message-ai'}`}
        >
          <div className="message-header">
            <span className="message-sender">
              {message.role === 'user' ? 'You' : 'ARCHITECT'}
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
            <span className="message-sender">ARCHITECT</span>
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
