import { useState, useRef, useEffect } from 'react';
import type { Document } from '../../types';
import ConfirmDialog from '../ConfirmDialog/ConfirmDialog';
import './DocumentTabs.css';

interface DocumentTabsProps {
  documents: Document[];
  activeDocumentId: string | null;
  onDocumentSelect: (docId: string) => void;
  onRenameDocument?: (docId: string, newTitle: string) => void;
  onDeleteDocument?: (docId: string) => void;
}

export default function DocumentTabs({
  documents,
  activeDocumentId,
  onDocumentSelect,
  onRenameDocument,
  onDeleteDocument,
}: DocumentTabsProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<{ isOpen: boolean; docId: string | null }>({
    isOpen: false,
    docId: null,
  });
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingId]);

  if (documents.length === 0) return null;

  const handleDoubleClick = (doc: Document) => {
    if (!onRenameDocument) return;
    setEditingId(doc.id);
    setEditValue(doc.title);
  };

  const handleRenameSubmit = () => {
    if (editingId && editValue.trim() && onRenameDocument) {
      onRenameDocument(editingId, editValue.trim());
    }
    setEditingId(null);
  };

  const handleRenameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleRenameSubmit();
    } else if (e.key === 'Escape') {
      setEditingId(null);
    }
  };

  const handleDelete = (e: React.MouseEvent, docId: string) => {
    e.stopPropagation();
    setDeleteConfirm({ isOpen: true, docId });
  };

  return (
    <div className="document-tabs-container">
      <div className="document-tabs">
        {documents.map((doc) => (
          <button
            key={doc.id}
            className={`document-tab ${doc.id === activeDocumentId ? 'active' : ''}`}
            onClick={() => onDocumentSelect(doc.id)}
            onDoubleClick={() => handleDoubleClick(doc)}
            title={doc.title}
          >
            {editingId === doc.id ? (
              <input
                ref={inputRef}
                className="tab-rename-input"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                onKeyDown={handleRenameKeyDown}
                onBlur={handleRenameSubmit}
                onClick={(e) => e.stopPropagation()}
                maxLength={200}
              />
            ) : (
              <span className="tab-title">{doc.title}</span>
            )}
            {editingId !== doc.id && onRenameDocument && (
              <span
                className="tab-rename-icon"
                role="button"
                tabIndex={0}
                onClick={(e) => {
                  e.stopPropagation();
                  handleDoubleClick(doc);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.stopPropagation();
                    handleDoubleClick(doc);
                  }
                }}
                title="Rename document"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                </svg>
              </span>
            )}
            {documents.length > 1 && onDeleteDocument && editingId !== doc.id && (
              <span
                className="tab-close-btn"
                role="button"
                tabIndex={0}
                onClick={(e) => handleDelete(e, doc.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleDelete(e as unknown as React.MouseEvent, doc.id);
                }}
                title="Close document"
              >
                &times;
              </span>
            )}
          </button>
        ))}
      </div>
      <ConfirmDialog
        isOpen={deleteConfirm.isOpen}
        title="Delete Document?"
        message="This cannot be undone. All versions will be permanently deleted."
        onConfirm={() => {
          if (deleteConfirm.docId && onDeleteDocument) {
            onDeleteDocument(deleteConfirm.docId);
          }
        }}
        onCancel={() => setDeleteConfirm({ isOpen: false, docId: null })}
        confirmText="Delete"
        cancelText="Keep Document"
        danger
      />
    </div>
  );
}
