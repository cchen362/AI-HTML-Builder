import React from 'react';
import { Link } from 'react-router-dom';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import type { Message } from '../../types';
import './ChatWindow.css';

interface ChatWindowProps {
  sessionId: string;
  messages: Message[];
  onSendMessage: (message: string, files?: File[]) => void;
  isProcessing?: boolean;
}

const ChatWindow: React.FC<ChatWindowProps> = ({
  sessionId,
  messages,
  onSendMessage,
  isProcessing = false
}) => {
  return (
    <div className="chat-window">
      <div className="chat-header">
        <h2>AI HTML Builder</h2>
        <div className="session-info">
          <div className="session-status-row">
            <span className="session-id">Session: {sessionId.slice(0, 8)}...</span>
            <Link to="/admin" className="admin-header-link">
              🔐 Admin
            </Link>
          </div>
          <div className={`status-indicator ${isProcessing ? 'processing' : 'ready'}`}>
            {isProcessing ? 'Generating...' : 'Ready'}
          </div>
        </div>
      </div>
      
      <MessageList 
        messages={messages} 
        isProcessing={isProcessing}
      />
      
      <ChatInput 
        onSendMessage={onSendMessage}
        isProcessing={isProcessing}
        placeholder="Describe the HTML you want to create..."
      />
    </div>
  );
};

export default ChatWindow;