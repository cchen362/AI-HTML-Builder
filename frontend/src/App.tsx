import React, { useState } from 'react'
import SplitPane from './components/Layout/SplitPane'
import { useWebSocket } from './hooks/useWebSocket'
import './App.css'

// Inline types to avoid import issues
interface Message {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: number;
}

// Chat window component
const ChatWindow = React.memo(({ 
  sessionId, 
  messages, 
  isProcessing, 
  isConnected, 
  error, 
  inputValue, 
  setInputValue, 
  handleSendMessage 
}: {
  sessionId: string;
  messages: Message[];
  isProcessing: boolean;
  isConnected: boolean;
  error: string | null;
  inputValue: string;
  setInputValue: (value: string) => void;
  handleSendMessage: () => void;
}) => (
  <div className="chat-window">
    <div className="chat-header">
      <h2>AI HTML Builder</h2>
      <div className="session-info">
        <span className="session-id">Session: {sessionId.slice(0, 8)}</span>
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </div>
      </div>
    </div>
    
    {error && (
      <div className="error-banner">
        ⚠️ {error}
      </div>
    )}
    
    <div className="messages">
      {messages.length === 0 && (
        <div className="welcome-message">
          <h3>Welcome to AI HTML Builder!</h3>
          <p>Describe the HTML you want to create and I'll generate it for you.</p>
          <div className="examples">
            <strong>Try these examples:</strong>
            <ul>
              <li>"Create a business card"</li>
              <li>"Make a landing page"</li>
              <li>"Build a pricing table"</li>
            </ul>
          </div>
        </div>
      )}
      
      {messages.map((message) => (
        <div key={message.id} className={`message ${message.sender}`}>
          <div className="message-header">
            <span className="sender">{message.sender === 'user' ? 'You' : 'AI Assistant'}</span>
            <span className="timestamp">{new Date(message.timestamp).toLocaleTimeString()}</span>
          </div>
          <div className="message-content">{message.content}</div>
        </div>
      ))}
      
      {isProcessing && (
        <div className="message ai processing">
          <div className="message-header">
            <span className="sender">AI Assistant</span>
            <span className="timestamp">Processing...</span>
          </div>
          <div className="message-content">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
            Generating HTML content...
          </div>
        </div>
      )}
    </div>
    
    <div className="chat-input">
      <textarea
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        placeholder="Describe the HTML you want..."
        rows={3}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
          }
        }}
      />
      <button 
        onClick={handleSendMessage} 
        disabled={!inputValue.trim() || isProcessing || !isConnected}
      >
        Send
      </button>
    </div>
  </div>
))

// HTML viewer component
const HtmlViewer = React.memo(({ 
  currentHtml, 
  viewMode, 
  setViewMode, 
  handleExport 
}: {
  currentHtml: string;
  viewMode: 'preview' | 'code';
  setViewMode: (mode: 'preview' | 'code') => void;
  handleExport: () => void;
}) => (
  <div className="html-viewer">
    <div className="viewer-header">
      <div className="view-controls">
        <button 
          className={viewMode === 'preview' ? 'active' : ''} 
          onClick={() => setViewMode('preview')}
        >
          🔍 Preview
        </button>
        <button 
          className={viewMode === 'code' ? 'active' : ''} 
          onClick={() => setViewMode('code')}
        >
          📄 Code
        </button>
      </div>
      <button className="export-btn" onClick={handleExport} disabled={!currentHtml}>
        📥 Export
      </button>
    </div>
    
    <div className="viewer-content">
      {!currentHtml ? (
        <div className="placeholder">
          <h3>No content yet</h3>
          <p>Send a message to generate HTML content</p>
        </div>
      ) : viewMode === 'preview' ? (
        <iframe
          srcDoc={currentHtml}
          title="Generated HTML Preview"
          className="html-preview"
        />
      ) : (
        <pre className="html-code">
          <code>{currentHtml}</code>
        </pre>
      )}
    </div>
  </div>
))

function App() {
  const [sessionId] = useState(() => crypto.randomUUID())
  const [inputValue, setInputValue] = useState('')
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview')
  
  // Use WebSocket hook for real-time communication
  const { 
    messages, 
    currentHtml, 
    isProcessing, 
    sendMessage, 
    isConnected, 
    error 
  } = useWebSocket(sessionId)

  const handleSendMessage = React.useCallback(() => {
    if (!inputValue.trim()) return;
    
    sendMessage(inputValue)
    setInputValue('')
  }, [inputValue, sendMessage])

  const handleExport = React.useCallback(() => {
    if (!currentHtml) return;
    
    const blob = new Blob([currentHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'generated-page.html';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }, [currentHtml])

  return (
    <div className="App">
      <SplitPane
        leftContent={
          <ChatWindow 
            sessionId={sessionId}
            messages={messages}
            isProcessing={isProcessing}
            isConnected={isConnected}
            error={error}
            inputValue={inputValue}
            setInputValue={setInputValue}
            handleSendMessage={handleSendMessage}
          />
        }
        rightContent={
          <HtmlViewer 
            currentHtml={currentHtml}
            viewMode={viewMode}
            setViewMode={setViewMode}
            handleExport={handleExport}
          />
        }
        defaultPosition={50}
        minSize={30}
        maxSize={70}
      />
    </div>
  )
}

export default App