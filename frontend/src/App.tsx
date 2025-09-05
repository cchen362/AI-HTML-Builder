import React, { useState } from 'react'
import SplitPane from './components/Layout/SplitPane'
import ChatWindow from './components/ChatWindow'
import { useWebSocket } from './hooks/useWebSocket'
import './App.css'

// HTML viewer component
const HtmlViewer = React.memo(({ 
  currentHtml, 
  viewMode, 
  setViewMode, 
  handleExport,
  handleFullScreen
}: {
  currentHtml: string;
  viewMode: 'preview' | 'code';
  setViewMode: (mode: 'preview' | 'code') => void;
  handleExport: () => void;
  handleFullScreen: () => void;
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
      <div className="viewer-actions">
        <button 
          className="fullscreen-btn" 
          onClick={handleFullScreen} 
          disabled={!currentHtml}
          title="Open in new tab"
        >
          🔗 Full Screen
        </button>
        <button className="export-btn" onClick={handleExport} disabled={!currentHtml}>
          📥 Export
        </button>
      </div>
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
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview')
  
  // Use WebSocket hook for real-time communication
  const { 
    messages, 
    currentHtml, 
    isProcessing, 
    sendMessage
  } = useWebSocket(sessionId)

  const handleSendMessage = React.useCallback((message: string) => {
    if (message.trim()) {
      sendMessage(message);
    }
  }, [sendMessage])

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

  const handleFullScreen = React.useCallback(() => {
    if (!currentHtml) return;
    
    const blob = new Blob([currentHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const newWindow = window.open(url, '_blank');
    
    // Clean up the URL after a delay to allow the window to load
    setTimeout(() => {
      URL.revokeObjectURL(url);
    }, 5000);
    
    // Focus the new window if it opened successfully
    if (newWindow) {
      newWindow.focus();
    }
  }, [currentHtml])

  return (
    <div className="App">
      <SplitPane
        leftContent={
          <ChatWindow 
            sessionId={sessionId}
            messages={messages}
            onSendMessage={handleSendMessage}
            isProcessing={isProcessing}
          />
        }
        rightContent={
          <HtmlViewer 
            currentHtml={currentHtml}
            viewMode={viewMode}
            setViewMode={setViewMode}
            handleExport={handleExport}
            handleFullScreen={handleFullScreen}
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