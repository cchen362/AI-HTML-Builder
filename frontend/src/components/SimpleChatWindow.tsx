import React from 'react';

interface SimpleChatWindowProps {
  sessionId: string;
}

const SimpleChatWindow: React.FC<SimpleChatWindowProps> = ({ sessionId }) => {
  return (
    <div style={{ 
      height: '100%', 
      background: 'white', 
      display: 'flex', 
      flexDirection: 'column' 
    }}>
      <div style={{ 
        padding: '1rem', 
        background: '#003366', 
        color: 'white' 
      }}>
        <h2>AI HTML Builder</h2>
        <div>Session: {sessionId.slice(0, 8)}...</div>
      </div>
      
      <div style={{ 
        flex: 1, 
        padding: '1rem', 
        background: '#f8f9fa' 
      }}>
        <p>Messages will appear here</p>
      </div>
      
      <div style={{ 
        padding: '1rem', 
        borderTop: '1px solid #e5e5e5' 
      }}>
        <textarea 
          placeholder="Type your message here..." 
          style={{ 
            width: '100%', 
            padding: '0.5rem', 
            border: '1px solid #ccc',
            borderRadius: '4px'
          }}
        />
        <button style={{ 
          marginTop: '0.5rem', 
          padding: '0.5rem 1rem',
          background: '#003366',
          color: 'white',
          border: 'none',
          borderRadius: '4px'
        }}>
          Send
        </button>
      </div>
    </div>
  );
};

export default SimpleChatWindow;