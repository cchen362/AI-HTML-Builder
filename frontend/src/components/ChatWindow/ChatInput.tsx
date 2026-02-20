import React, { useState, useRef, useEffect, useCallback } from 'react';
import PromptLibraryButton from './PromptLibraryButton';
import PromptLibraryModal from './PromptLibraryModal';
import BrandSelector from './BrandSelector';
import { uploadFile, validateFileClient, type UploadResponse } from '../../services/uploadService';
import type { PromptTemplate } from '../../data/promptTemplates';
import './ChatInput.css';

interface ChatInputProps {
  onSendMessage: (message: string, files?: File[], templateName?: string, userContent?: string, brandId?: string) => void;
  isProcessing?: boolean;
  placeholder?: string;
  externalTemplate?: PromptTemplate | null;
  onExternalTemplateClaimed?: () => void;
  onCancelRequest?: () => void;
}

// Custom hook for auto-resize based on 2025 best practices
const useAutosizeTextArea = (
  textAreaRef: React.RefObject<HTMLTextAreaElement | null>,
  value: string
) => {
  useEffect(() => {
    if (textAreaRef.current) {
      // Reset height to shrink on delete
      textAreaRef.current.style.height = 'inherit';
      // Calculate the height
      const computed = window.getComputedStyle(textAreaRef.current);
      const height = parseInt(computed.getPropertyValue('border-top-width'), 10)
                   + parseInt(computed.getPropertyValue('padding-top'), 10)
                   + textAreaRef.current.scrollHeight
                   + parseInt(computed.getPropertyValue('padding-bottom'), 10)
                   + parseInt(computed.getPropertyValue('border-bottom-width'), 10);

      // Set max height to 30% of viewport as per research
      const maxHeight = Math.floor(window.innerHeight * 0.3);
      const finalHeight = Math.min(height, maxHeight);

      textAreaRef.current.style.height = `${finalHeight}px`;
    }
  }, [textAreaRef, value]);
};

// Inline popover for template preview ("what did I pick?")
const TemplatePopover: React.FC<{
  template: PromptTemplate;
  onClose: () => void;
}> = ({ template, onClose }) => {
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    // Delay listener to avoid immediate close from the click that opened it
    const timer = setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleEscape);
    }, 0);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [onClose]);

  const previewText = template.template
    .replace(/\{\{[A-Z_]+\}\}/g, '[Your content here]');

  return (
    <div className="template-popover" ref={popoverRef}>
      <div className="template-popover-header">
        <span className="template-popover-title">{template.name}</span>
        <span className="template-popover-category">{template.category}</span>
      </div>
      <div className="template-popover-body">
        {previewText.split('\n').map((line, i) => (
          <div key={i} className={
            /^[A-Z][A-Z _/&()-]+:/.test(line) ? 'popover-section-header' : 'popover-line'
          }>
            {line || '\u00A0'}
          </div>
        ))}
      </div>
    </div>
  );
};

const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isProcessing = false,
  placeholder = "Describe the HTML you want to create, or browse templates for inspiration...",
  externalTemplate = null,
  onExternalTemplateClaimed,
  onCancelRequest,
}) => {
  const [message, setMessage] = useState('');
  const [showLargeContentHint, setShowLargeContentHint] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Template badge state
  const [activeTemplate, setActiveTemplate] = useState<PromptTemplate | null>(null);
  const [popoverOpen, setPopoverOpen] = useState(false);

  // File upload state
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [attachedFile, setAttachedFile] = useState<{ name: string } | null>(null);

  // Drag-and-drop state
  const [isDragging, setIsDragging] = useState(false);
  const dragCountRef = useRef(0);

  // Brand selection state (persisted in localStorage)
  const [activeBrandId, setActiveBrandId] = useState<string | null>(
    () => localStorage.getItem('selected_brand_id')
  );

  const handleBrandChange = useCallback((brandId: string | null) => {
    setActiveBrandId(brandId);
    if (brandId) {
      localStorage.setItem('selected_brand_id', brandId);
    } else {
      localStorage.removeItem('selected_brand_id');
    }
  }, []);

  // Use the custom hook for auto-resize
  useAutosizeTextArea(textareaRef, message);

  // Receive external template (e.g. from template card click) — activate badge
  useEffect(() => {
    if (externalTemplate) {
      setActiveTemplate(externalTemplate);
      setPopoverOpen(false);
      setMessage('');
      setAttachedFile(null);
      onExternalTemplateClaimed?.();
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  }, [externalTemplate, onExternalTemplateClaimed]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isProcessing) return;

    if (activeTemplate) {
      const userContent = message.trim();
      const fullMessage = userContent
        ? `${activeTemplate.template}\n\n${userContent}`
        : activeTemplate.template;
      onSendMessage(fullMessage, undefined, activeTemplate.name, userContent || '(template only)', activeBrandId ?? undefined);
      setMessage('');
      setActiveTemplate(null);
      setPopoverOpen(false);
      setShowLargeContentHint(false);
      setAttachedFile(null);
    } else if (message.trim()) {
      onSendMessage(message.trim(), undefined, undefined, undefined, activeBrandId ?? undefined);
      setMessage('');
      setShowLargeContentHint(false);
      setAttachedFile(null);
    }
  };

  const handleMessageChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setMessage(value);

    // Show hint for large content
    if (value.length > 500 && !showLargeContentHint) {
      setShowLargeContentHint(true);
    } else if (value.length <= 500 && showLargeContentHint) {
      setShowLargeContentHint(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleTemplateSelect = (template: PromptTemplate) => {
    setActiveTemplate(template);
    setPopoverOpen(false);
    setMessage('');
    setAttachedFile(null);
    setTimeout(() => textareaRef.current?.focus(), 100);
  };

  const handleRemoveTemplate = useCallback(() => {
    setActiveTemplate(null);
    setPopoverOpen(false);
  }, []);

  // --- File upload handlers ---

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    // Reset input so same file can be selected again
    e.target.value = '';

    const validationError = validateFileClient(file);
    if (validationError) {
      setUploadError(validationError);
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    try {
      const result: UploadResponse = await uploadFile(file);
      if (activeTemplate) {
        setMessage(result.data.content);
      } else {
        setMessage(result.suggested_prompt);
      }
      setAttachedFile({ name: result.data.filename });
      textareaRef.current?.focus();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleClearAttachment = () => {
    setAttachedFile(null);
  };

  // --- Drag-and-drop handlers ---

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCountRef.current += 1;
    if (dragCountRef.current === 1) setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCountRef.current -= 1;
    if (dragCountRef.current === 0) setIsDragging(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCountRef.current = 0;
    setIsDragging(false);

    const file = e.dataTransfer.files[0];
    if (!file) return;

    const validationError = validateFileClient(file);
    if (validationError) {
      setUploadError(validationError);
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    try {
      const result: UploadResponse = await uploadFile(file);
      if (activeTemplate) {
        setMessage(result.data.content);
      } else {
        setMessage(result.suggested_prompt);
      }
      setAttachedFile({ name: result.data.filename });
      textareaRef.current?.focus();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <form
      className={`chat-input-container${isDragging ? ' dragging' : ''}`}
      onSubmit={handleSubmit}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {isDragging && (
        <div className="drop-overlay">
          <span>{activeTemplate ? `Drop file for ${activeTemplate.name}` : 'Drop file here'}</span>
        </div>
      )}
      {uploadError && (
        <div className="upload-error-banner">
          <span>{uploadError}</span>
          <button type="button" onClick={() => setUploadError(null)}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>
      )}

      {attachedFile && (
        <div className="attached-file-indicator">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="file-icon">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zM14 3.5L18.5 8H14V3.5zM6 20V4h7v5h5v11H6z"/>
          </svg>
          <span className="attached-file-name">{attachedFile.name}</span>
          <button type="button" onClick={handleClearAttachment} className="remove-attachment" title="Remove file">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>
      )}

      {activeTemplate && (
        <div className="template-badge-bar">
          <div className="template-badge">
            <span className="template-badge-icon">&#x1F4CB;</span>
            <span
              className="template-badge-name"
              role="button"
              tabIndex={0}
              onClick={() => setPopoverOpen(prev => !prev)}
              onKeyDown={(e) => { if (e.key === 'Enter') setPopoverOpen(prev => !prev); }}
            >
              {activeTemplate.name}
            </span>
            <button
              type="button"
              className="template-badge-remove"
              onClick={handleRemoveTemplate}
              title="Remove template"
            >
              &times;
            </button>
          </div>
          {popoverOpen && (
            <TemplatePopover
              template={activeTemplate}
              onClose={() => setPopoverOpen(false)}
            />
          )}
        </div>
      )}

      {showLargeContentHint && (
        <div className="content-hint">
          <span className="hint-icon">&#x1F4A1;</span>
          <span>I can see you've pasted detailed content - I'll transform this into beautiful HTML!</span>
        </div>
      )}

      <div className="input-wrapper">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={handleMessageChange}
          onKeyDown={handleKeyDown}
          placeholder={
            activeTemplate && attachedFile
              ? 'Add extra instructions (optional) — file content will be used as source material'
              : activeTemplate
                ? `Add your content for "${activeTemplate.name}"... (or send directly to use template defaults)`
                : placeholder
          }
          disabled={isProcessing}
          className="chat-textarea"
          rows={1}
        />

        {isProcessing && onCancelRequest ? (
          <button type="button" className="cancel-button" onClick={onCancelRequest} title="Cancel generation">
            Cancel
          </button>
        ) : (
          <button
            type="submit"
            disabled={(!message.trim() && !activeTemplate) || isProcessing}
            className="send-button"
            title="Send message (Enter)"
          >
            {isProcessing ? (
              <div className="loading-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2,21L23,12L2,3V10L17,12L2,14V21Z" />
              </svg>
            )}
          </button>
        )}
      </div>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt,.md,.docx,.pdf,.csv,.xlsx"
        onChange={handleFileSelect}
        style={{ display: 'none' }}
      />

      <div className="input-footer">
        <div className="footer-left">
          <button
            type="button"
            className="attach-file-btn"
            disabled={isProcessing || isUploading}
            onClick={() => fileInputRef.current?.click()}
            title="Upload a file (.txt, .md, .docx, .pdf, .csv, .xlsx)"
          >
            {isUploading ? 'Uploading...' : 'Attach File'}
          </button>
          <PromptLibraryButton
            onClick={() => setIsModalOpen(true)}
            disabled={isProcessing}
          />
          <BrandSelector
            activeBrandId={activeBrandId}
            onBrandChange={handleBrandChange}
            disabled={isProcessing}
          />
        </div>
        <div className="footer-right">
          <span className="char-count">{message.length.toLocaleString()} chars</span>
          <span className="help-text">Shift + Enter for new line</span>
        </div>
      </div>

      <PromptLibraryModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSelectTemplate={handleTemplateSelect}
      />
    </form>
  );
};

export default ChatInput;
