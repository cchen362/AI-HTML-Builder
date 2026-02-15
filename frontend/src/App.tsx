import React, { useState, useCallback, useMemo, useEffect } from 'react'
import SplitPane from './components/Layout/SplitPane'
import ChatWindow from './components/ChatWindow'
import { useSSEChat } from './hooks/useSSEChat'
import CodeView from './components/CodeViewer/CodeView'
import DocumentTabs from './components/DocumentTabs/DocumentTabs'
import VersionTimeline from './components/VersionHistory/VersionTimeline'
import ExportDropdown from './components/Export/ExportDropdown'
import { api } from './services/api'
import ConfirmDialog from './components/ConfirmDialog/ConfirmDialog'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import LoginPage from './components/Auth/LoginPage'
import SetupPage from './components/Auth/SetupPage'
import AdminPanel from './components/Auth/AdminPanel'
import HomeScreen from './components/HomeScreen/HomeScreen'
import MySessionsModal from './components/HomeScreen/MySessionsModal'
import type { Document, User, SessionSummary } from './types'
import { humanizeError } from './utils/errorUtils'
import type { PromptTemplate } from './data/promptTemplates'
import './App.css'

// HTML viewer component with version history side panel
const HtmlViewer = React.memo(({
  currentHtml,
  viewMode,
  setViewMode,
  handleExport,
  handleFullScreen,
  documents,
  activeDocumentId,
  documentTitle,
  onDocumentSelect,
  historyOpen,
  onToggleHistory,
  previewHtml,
  onVersionPreview,
  onBackToCurrent,
  onRestoreVersion,
  isStreaming,
  currentStatus,
  onRenameDocument,
  onDeleteDocument,
  onCodeViewSaved,
  onDirtyChange,
  isInfographic,
}: {
  currentHtml: string;
  viewMode: 'preview' | 'code';
  setViewMode: (mode: 'preview' | 'code') => void;
  handleExport: () => void;
  handleFullScreen: () => void;
  documents: Document[];
  activeDocumentId: string | null;
  documentTitle?: string;
  onDocumentSelect: (id: string) => void;
  historyOpen: boolean;
  onToggleHistory: () => void;
  previewHtml: string | null;
  onVersionPreview: (html: string) => void;
  onBackToCurrent: () => void;
  onRestoreVersion: (version: number) => void;
  isStreaming: boolean;
  currentStatus: string;
  onRenameDocument?: (docId: string, newTitle: string) => void;
  onDeleteDocument?: (docId: string) => void;
  onCodeViewSaved?: () => void;
  onDirtyChange?: (dirty: boolean) => void;
  isInfographic?: boolean;
}) => {
  const displayHtml = previewHtml ?? currentHtml;

  return (
    <div className="html-viewer">
      <DocumentTabs
        documents={documents}
        activeDocumentId={activeDocumentId}
        onDocumentSelect={onDocumentSelect}
        onRenameDocument={onRenameDocument}
        onDeleteDocument={onDeleteDocument}
      />
      <div className="viewer-header">
        <div className="view-controls">
          <button
            className={viewMode === 'preview' ? 'active' : ''}
            onClick={() => setViewMode('preview')}
          >
            Preview
          </button>
          <button
            className={viewMode === 'code' ? 'active' : ''}
            onClick={() => setViewMode('code')}
          >
            Code
          </button>
        </div>
        <div className="viewer-actions">
          <div className="action-group action-group--primary">
            <button
              className={`history-btn${historyOpen ? ' active' : ''}`}
              onClick={onToggleHistory}
              disabled={!activeDocumentId}
              title="Version history"
            >
              History
            </button>
            <ExportDropdown
              onExportHtml={handleExport}
              disabled={!currentHtml}
              documentId={activeDocumentId}
              documentTitle={documentTitle}
              isInfographic={isInfographic}
            />
          </div>
          <button
            className="fullscreen-btn"
            onClick={handleFullScreen}
            disabled={!currentHtml}
            title="Open in new tab"
          >
            Full Screen
          </button>
        </div>
      </div>

      <div className="viewer-body">
        <div className="viewer-content">
          {!displayHtml ? (
            isStreaming ? (
              <div className="viewer-loading">
                <div className="loading-glyph">&lt;/&gt;</div>
                {currentStatus && <p className="loading-status">{currentStatus}</p>}
              </div>
            ) : (
              <div className="placeholder">
                <h3>No content yet</h3>
                <p>Send a message to generate HTML content</p>
              </div>
            )
          ) : viewMode === 'preview' ? (
            <iframe
              srcDoc={displayHtml}
              title="Generated HTML Preview"
              className="html-preview"
            />
          ) : (
            <CodeView
              html={displayHtml}
              documentId={activeDocumentId}
              onSaved={onCodeViewSaved}
              isStreaming={isStreaming}
              onDirtyChange={onDirtyChange}
            />
          )}
        </div>

        <VersionTimeline
          documentId={activeDocumentId}
          onVersionPreview={onVersionPreview}
          onBackToCurrent={onBackToCurrent}
          onRestoreVersion={onRestoreVersion}
          isOpen={historyOpen}
          onToggle={onToggleHistory}
        />
      </div>
    </div>
  );
})

// Main chat application component
const ChatApp = ({ user }: { user: User }) => {
  const [viewMode, setViewMode] = useState<'preview' | 'code'>('preview')
  const [error, setError] = useState<string | null>(null)
  const [historyOpen, setHistoryOpen] = useState(false)
  const [previewHtml, setPreviewHtml] = useState<string | null>(null)
  const [newSessionConfirm, setNewSessionConfirm] = useState(false)
  const [isCodeViewDirty, setIsCodeViewDirty] = useState(false)
  const [adminOpen, setAdminOpen] = useState(false)
  const [mySessionsOpen, setMySessionsOpen] = useState(false)
  const [recentSessions, setRecentSessions] = useState<SessionSummary[]>([])
  const { logout } = useAuth()
  const {
    sessionId,
    messages,
    isStreaming,
    currentStatus,
    streamingContent,
    currentHtml,
    sendMessage,
    cancelRequest,
    documents,
    activeDocument,
    switchDocument,
    refreshDocuments,
    isInitializing,
    startNewSession,
    showHomeScreen,
    loadSession,
    sendFirstMessage,
  } = useSSEChat({
    onError: (msg) => setError(msg),
  })

  const isInfographic = useMemo(() => {
    if (!currentHtml) return false;
    const stripped = currentHtml.replace(
      /data:image\/[^;]+;base64,[A-Za-z0-9+/=]{100,}/g, ''
    );
    return stripped.length < 600
      && currentHtml.includes('data:image')
      && !/<(main|header|section)/i.test(currentHtml);
  }, [currentHtml]);

  // Load recent sessions when home screen is shown
  useEffect(() => {
    if (showHomeScreen) {
      api.listSessions(3, 0)
        .then(({ sessions }) => setRecentSessions(sessions))
        .catch(() => setRecentSessions([]));
    }
  }, [showHomeScreen]);

  const handleSendMessage = useCallback((message: string, _files?: File[], templateName?: string, userContent?: string) => {
    if (isCodeViewDirty && viewMode === 'code') {
      setError('Save or discard your HTML changes before sending a message.')
      return
    }
    if (message.trim()) {
      setError(null)
      sendMessage(message, activeDocument?.id, templateName, userContent)
    }
  }, [sendMessage, activeDocument, isCodeViewDirty, viewMode])

  const handleStartNewSession = useCallback(() => {
    setNewSessionConfirm(true)
  }, [])

  const confirmNewSession = useCallback(() => {
    startNewSession()
  }, [startNewSession])

  const handleSelectSession = useCallback(async (targetSessionId: string) => {
    await loadSession(targetSessionId)
    setMySessionsOpen(false)
  }, [loadSession])

  const handleHomeTemplate = useCallback((template: PromptTemplate) => {
    sendFirstMessage(template.template, template.name, '(template only)')
  }, [sendFirstMessage])

  const handleHomeSendMessage = useCallback((
    message: string, _files?: File[], templateName?: string, userContent?: string
  ) => {
    if (message.trim()) {
      sendFirstMessage(message, templateName, userContent)
    }
  }, [sendFirstMessage])

  const handleOpenMySessions = useCallback(() => {
    setMySessionsOpen(true)
  }, [])

  const handleExport = useCallback(() => {
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

  const handleFullScreen = useCallback(() => {
    if (!currentHtml) return;

    const blob = new Blob([currentHtml], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const newWindow = window.open(url, '_blank');

    setTimeout(() => {
      URL.revokeObjectURL(url);
    }, 5000);

    if (newWindow) {
      newWindow.focus();
    }
  }, [currentHtml])

  const handleToggleHistory = useCallback(() => {
    setHistoryOpen(prev => !prev)
    setPreviewHtml(null)
  }, [])

  const handleVersionPreview = useCallback((html: string) => {
    setPreviewHtml(html)
  }, [])

  const handleBackToCurrent = useCallback(() => {
    setPreviewHtml(null)
  }, [])

  const handleRestoreVersion = useCallback(async (version: number) => {
    if (!activeDocument?.id) return;
    try {
      await api.restoreVersion(activeDocument.id, version);
      setPreviewHtml(null);
      await refreshDocuments();
      setHistoryOpen(false);
      setTimeout(() => setHistoryOpen(true), 50);
    } catch (err) {
      setError(humanizeError(err));
    }
  }, [activeDocument, refreshDocuments])

  const handleRenameDocument = useCallback(async (docId: string, newTitle: string) => {
    try {
      await api.renameDocument(docId, newTitle);
      await refreshDocuments();
    } catch (err) {
      setError(humanizeError(err));
    }
  }, [refreshDocuments])

  const handleDeleteDocument = useCallback(async (docId: string) => {
    if (!sessionId) return;
    try {
      await api.deleteDocument(sessionId, docId);
      await refreshDocuments();
    } catch (err) {
      setError(humanizeError(err));
    }
  }, [sessionId, refreshDocuments])

  const handleCodeViewSaved = useCallback(async () => {
    await refreshDocuments()
    if (historyOpen) {
      setHistoryOpen(false)
      setTimeout(() => setHistoryOpen(true), 50)
    }
  }, [refreshDocuments, historyOpen])

  const handleLogout = useCallback(async () => {
    await logout()
  }, [logout])

  if (isInitializing) {
    return (
      <div className="App">
        <div className="app-loading">
          <div className="loading-glyph">[&#9608;]</div>
          <div className="loading-text">INITIALIZING...</div>
        </div>
      </div>
    )
  }

  // Home screen — shown on login or after "New Session"
  if (showHomeScreen) {
    return (
      <div className="App">
        <HomeScreen
          user={user}
          recentSessions={recentSessions}
          onSelectSession={handleSelectSession}
          onSelectTemplate={handleHomeTemplate}
          onSendMessage={handleHomeSendMessage}
          onViewAllSessions={handleOpenMySessions}
        />
        <MySessionsModal
          isOpen={mySessionsOpen}
          onClose={() => setMySessionsOpen(false)}
          onSelectSession={handleSelectSession}
          currentSessionId={sessionId}
        />
      </div>
    )
  }

  return (
    <div className="App">
      <SplitPane
        leftContent={
          <ChatWindow
            messages={messages}
            onSendMessage={handleSendMessage}
            isStreaming={isStreaming}
            streamingContent={streamingContent}
            error={error}
            onDismissError={() => setError(null)}
            onCancelRequest={cancelRequest}
            sessionId={sessionId}
            onStartNewSession={handleStartNewSession}
            documents={documents}
            user={user}
            onAdminSettings={() => setAdminOpen(true)}
            onLogout={handleLogout}
            onOpenMySessions={handleOpenMySessions}
          />
        }
        rightContent={
          <HtmlViewer
            currentHtml={currentHtml}
            viewMode={viewMode}
            setViewMode={setViewMode}
            handleExport={handleExport}
            handleFullScreen={handleFullScreen}
            documents={documents}
            activeDocumentId={activeDocument?.id ?? null}
            documentTitle={activeDocument?.title}
            onDocumentSelect={switchDocument}
            historyOpen={historyOpen}
            onToggleHistory={handleToggleHistory}
            previewHtml={previewHtml}
            onVersionPreview={handleVersionPreview}
            onBackToCurrent={handleBackToCurrent}
            onRestoreVersion={handleRestoreVersion}
            isStreaming={isStreaming}
            currentStatus={currentStatus}
            onRenameDocument={handleRenameDocument}
            onDeleteDocument={handleDeleteDocument}
            onCodeViewSaved={handleCodeViewSaved}
            onDirtyChange={setIsCodeViewDirty}
            isInfographic={isInfographic}
          />
        }
        defaultPosition={50}
        minSize={30}
        maxSize={70}
      />
      <ConfirmDialog
        isOpen={newSessionConfirm}
        title="Start New Session?"
        message="Your current session will be saved. You'll return to the home screen."
        onConfirm={confirmNewSession}
        onCancel={() => setNewSessionConfirm(false)}
        confirmText="Start Fresh"
        cancelText="Stay Here"
      />
      <AdminPanel
        isOpen={adminOpen}
        onClose={() => setAdminOpen(false)}
        currentUserId={user.id}
      />
      <MySessionsModal
        isOpen={mySessionsOpen}
        onClose={() => setMySessionsOpen(false)}
        onSelectSession={handleSelectSession}
        currentSessionId={sessionId}
      />
    </div>
  )
}

// Auth gate — decides what to show based on auth state
function AuthGate() {
  const { user, isLoading, needsSetup } = useAuth()

  if (isLoading) {
    return (
      <div className="App">
        <div className="app-loading">
          <div className="loading-glyph">[&#9608;]</div>
          <div className="loading-text">LOADING...</div>
        </div>
      </div>
    )
  }

  if (needsSetup) return <SetupPage />
  if (!user) return <LoginPage />
  return <ChatApp user={user} />
}

function App() {
  return (
    <AuthProvider>
      <AuthGate />
    </AuthProvider>
  )
}

export default App
