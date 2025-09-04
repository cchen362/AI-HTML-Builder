import React, { useState, useRef, KeyboardEvent } from 'react';
import { FileInfo } from '../../types';
import './ChatInput.css';

interface ChatInputProps {
  onSendMessage: (message: string, files?: File[]) => void;
  isProcessing?: boolean;
  placeholder?: string;
}

const ChatInput: React.FC<ChatInputProps> = ({ 
  onSendMessage, 
  isProcessing = false,
  placeholder = "Describe the HTML you want to create..."
}) => {
  const [message, setMessage] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isProcessing) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const files = Array.from(e.dataTransfer.files);
      handleFileUpload(files);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files = Array.from(e.target.files);
      handleFileUpload(files);
    }
  };

  const handleFileUpload = (files: File[]) => {
    const validTypes = ['.txt', '.md', '.docx'];
    const validFiles = files.filter(file => {
      const extension = '.' + file.name.split('.').pop()?.toLowerCase();
      return validTypes.includes(extension) && file.size <= 50 * 1024 * 1024; // 50MB
    });

    if (validFiles.length > 0) {
      onSendMessage('', validFiles);
    }
  };

  return (
    <form 
      className={`chat-input ${dragActive ? 'drag-active' : ''}`}
      onSubmit={handleSubmit}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
    >
      <div className="input-container">
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder={placeholder}
          disabled={isProcessing}
          rows={3}
          className="message-input"
        />
        
        <div className="input-actions">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isProcessing}
            className="file-button"
            title="Upload file (.txt, .md, .docx)"
          >
            📎
          </button>
          
          <button
            type="submit"
            disabled={!message.trim() || isProcessing}
            className="send-button"
            title="Send message (Ctrl+Enter)"
          >
            {isProcessing ? '⏳' : '→'}
          </button>
        </div>
      </div>

      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileInput}
        accept=".txt,.md,.docx"
        multiple
        style={{ display: 'none' }}
      />

      <div className="input-help">
        Drop files here or click 📎 to upload • Ctrl+Enter to send
      </div>

      {dragActive && (
        <div className="drag-overlay">
          <div className="drag-message">
            Drop your files here
            <div className="drag-info">Supports .txt, .md, .docx (max 50MB)</div>
          </div>
        </div>
      )}
    </form>
  );
};

export default ChatInput;