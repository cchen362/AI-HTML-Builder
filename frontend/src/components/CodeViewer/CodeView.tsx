import { useState, useEffect, useCallback } from 'react';
import CodeMirrorViewer from './CodeMirrorViewer';
import CopyButton from './CopyButton';
import { api } from '../../services/api';
import './CodeView.css';

interface CodeViewProps {
  html: string;
  documentId?: string | null;
  onSaved?: () => void;
  isStreaming?: boolean;
  onDirtyChange?: (dirty: boolean) => void;
}

export default function CodeView({ html, documentId, onSaved, isStreaming, onDirtyChange }: CodeViewProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedHtml, setEditedHtml] = useState(html);
  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Reset when html prop changes (AI update or document switch)
  useEffect(() => {
    setEditedHtml(html);
    setIsDirty(false);
    setIsEditing(false);
    setSaveError(null);
  }, [html]);

  // Notify parent of dirty state changes
  useEffect(() => {
    onDirtyChange?.(isDirty);
  }, [isDirty, onDirtyChange]);

  const handleContentChange = useCallback((newCode: string) => {
    setEditedHtml(newCode);
    setIsDirty(newCode !== html);
  }, [html]);

  const handleToggleEdit = useCallback(() => {
    if (isEditing && isDirty) {
      // Exiting edit mode with unsaved changes — discard
      setEditedHtml(html);
      setIsDirty(false);
    }
    setIsEditing(prev => !prev);
    setSaveError(null);
  }, [isEditing, isDirty, html]);

  const handleSave = useCallback(async () => {
    if (!documentId || !isDirty) return;
    setIsSaving(true);
    setSaveError(null);
    try {
      await api.saveManualEdit(documentId, editedHtml);
      setIsDirty(false);
      setIsEditing(false);
      onSaved?.();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setIsSaving(false);
    }
  }, [documentId, isDirty, editedHtml, onSaved]);

  const handleDiscard = useCallback(() => {
    setEditedHtml(html);
    setIsDirty(false);
    setSaveError(null);
  }, [html]);

  return (
    <div className="code-view-container">
      <div className="code-view-header">
        <span className="code-view-title">
          HTML Source
          {isDirty && <span className="dirty-indicator">*</span>}
        </span>
        <div className="code-view-actions">
          {isDirty && isEditing && (
            <>
              <button
                className="code-discard-btn"
                onClick={handleDiscard}
                disabled={isSaving}
                type="button"
              >
                Discard
              </button>
              <button
                className="code-save-btn"
                onClick={handleSave}
                disabled={isSaving}
                type="button"
              >
                {isSaving ? 'Saving...' : 'Save Version'}
              </button>
            </>
          )}
          <button
            className={`edit-toggle-btn${isEditing ? ' active' : ''}`}
            onClick={handleToggleEdit}
            disabled={isStreaming}
            title={isEditing ? 'Exit edit mode' : 'Edit HTML'}
            type="button"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
            </svg>
          </button>
          <CopyButton text={isEditing ? editedHtml : html} label="Copy Code" />
        </div>
      </div>
      {saveError && (
        <div className="code-save-error">
          {saveError}
          <button type="button" onClick={() => setSaveError(null)}>×</button>
        </div>
      )}
      <div className="code-view-body">
        <CodeMirrorViewer
          code={isEditing ? editedHtml : html}
          onContentChange={isEditing ? handleContentChange : undefined}
          disabled={!isEditing}
        />
      </div>
    </div>
  );
}
