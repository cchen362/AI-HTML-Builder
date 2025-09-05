import React, { useEffect, useRef } from 'react';
import type { Message } from '../../types';
import './MessageList.css';

interface MessageListProps {
  messages: Message[];
  isProcessing?: boolean;
}

const MessageList: React.FC<MessageListProps> = ({ messages, isProcessing }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div className="message-list">
      {messages.map((message) => (
        <div 
          key={message.id} 
          className={`message ${message.sender === 'user' ? 'message-user' : 'message-ai'}`}
        >
          <div className="message-header">
            <span className="message-sender">
              {message.sender === 'user' ? 'You' : 'AI Assistant'}
            </span>
            <span className="message-timestamp">
              {formatTimestamp(message.timestamp)}
            </span>
          </div>
          <div className="message-content">
            {message.content}
          </div>
        </div>
      ))}
      
      {isProcessing && (
        <div className="message message-ai processing">
          <div className="message-header">
            <span className="message-sender">AI Assistant</span>
          </div>
          <div className="message-content">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
            Generating HTML...
          </div>
        </div>
      )}
      
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList;