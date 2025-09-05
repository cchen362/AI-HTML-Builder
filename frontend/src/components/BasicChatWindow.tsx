import React from 'react';
import type { Message } from '../types';

interface BasicChatWindowProps {
  sessionId: string;
  messages: Message[];
  onSendMessage: (message: string, files?: File[]) => void;
  isProcessing?: boolean;
}

const BasicChatWindow: React.FC<BasicChatWindowProps> = ({
  sessionId,
  messages,
  onSendMessage,
  isProcessing = false
}) => {
  const formatTimestamp = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  return (
    <div style={{ 
      height: '100%', 
      display: 'flex', 
      flexDirection: 'column',
      background: 'white'
    }}>
      <div style={{ 
        padding: '1rem', 
        background: 'linear-gradient(135deg, #003366, #004488)', 
        color: 'white' 
      }}>
        <h2 style={{ margin: 0 }}>AI HTML Builder</h2>
        <div style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>
          Session: {sessionId.slice(0, 8)}...
        </div>
      </div>
      
      {/* Inline Message List */}
      <div style={{ 
        flex: 1, 
        overflowY: 'auto', 
        padding: '1rem', 
        background: '#f8f9fa' 
      }}>
        {messages.length === 0 ? (
          <p style={{ color: '#6c757d', textAlign: 'center' }}>
            Start a conversation...
          </p>
        ) : (
          messages.map((message) => (
            <div 
              key={message.id}
              style={{
                maxWidth: '80%',
                padding: '0.75rem 1rem',
                marginBottom: '1rem',
                borderRadius: '12px',
                alignSelf: message.sender === 'user' ? 'flex-end' : 'flex-start',
                background: message.sender === 'user' ? '#003366' : 'white',
                color: message.sender === 'user' ? 'white' : '#333',
                border: message.sender === 'ai' ? '1px solid #e5e5e5' : 'none',
                marginLeft: message.sender === 'user' ? 'auto' : '0',
                marginRight: message.sender === 'user' ? '0' : 'auto'
              }}
            >
              <div style={{ 
                fontSize: '0.75rem', 
                opacity: 0.8, 
                marginBottom: '0.5rem',
                display: 'flex',
                justifyContent: 'space-between'
              }}>
                <span>{message.sender === 'user' ? 'You' : 'AI Assistant'}</span>
                <span>{formatTimestamp(message.timestamp)}</span>
              </div>
              <div>{message.content}</div>
            </div>
          ))
        )}
        
        {isProcessing && (
          <div style={{
            maxWidth: '80%',
            padding: '0.75rem 1rem',
            marginBottom: '1rem',
            borderRadius: '12px',
            background: 'white',
            border: '1px solid #e5e5e5',
            opacity: 0.8
          }}>
            <div style={{ fontSize: '0.75rem', opacity: 0.8, marginBottom: '0.5rem' }}>
              AI Assistant
            </div>
            <div>Generating HTML...</div>
          </div>
        )}
      </div>
      
      <div style={{ 
        padding: '1rem', 
        borderTop: '1px solid #e5e5e5' 
      }}>
        <textarea 
          placeholder="Describe the HTML you want to create..." 
          style={{ 
            width: '100%', 
            padding: '0.75rem', 
            border: '2px solid #e5e5e5',
            borderRadius: '8px',
            minHeight: '60px',
            resize: 'vertical',
            fontFamily: 'inherit'
          }}
        />
        <button 
          style={{ 
            marginTop: '0.5rem', 
            padding: '0.75rem 1rem',
            background: '#003366',
            color: 'white',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer'
          }}
          onClick={() => onSendMessage('Test message')}
        >
          Send
        </button>
      </div>
    </div>
  );
};

export default BasicChatWindow;