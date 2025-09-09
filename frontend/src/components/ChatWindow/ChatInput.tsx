import React, { useState, useRef, useEffect } from 'react';
import PromptLibraryButton from './PromptLibraryButton';
import PromptLibraryModal from './PromptLibraryModal';
import type { PromptTemplate } from '../../data/promptTemplates';
import './ChatInput.css';

interface ChatInputProps {
  onSendMessage: (message: string, files?: File[]) => void;
  isProcessing?: boolean;
  placeholder?: string;
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
      textAreaRef.current.style.overflowY = height > maxHeight ? 'auto' : 'hidden';
    }
  }, [textAreaRef, value]);
};

const ChatInput: React.FC<ChatInputProps> = ({ 
  onSendMessage, 
  isProcessing = false,
  placeholder = "Describe the HTML you want to create, or browse templates for inspiration..."
}) => {
  const [message, setMessage] = useState('');
  const [showLargeContentHint, setShowLargeContentHint] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  
  // Use the custom hook for auto-resize
  useAutosizeTextArea(textareaRef, message);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isProcessing) {
      onSendMessage(message.trim());
      setMessage('');
      setShowLargeContentHint(false);
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
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleTemplateSelect = (template: PromptTemplate) => {
    const templateText = template.template.replace('{USER_CONTENT}', '');
    setMessage(templateText);
    // Focus the textarea after inserting template
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        // Position cursor at the placeholder location
        const placeholderText = '[Your content here]';
        const withPlaceholder = templateText.replace(/\n\n$/, `\n\n${placeholderText}`);
        setMessage(withPlaceholder);
        
        // Select the placeholder text for easy replacement
        const startPos = withPlaceholder.indexOf(placeholderText);
        if (startPos !== -1) {
          textareaRef.current.setSelectionRange(startPos, startPos + placeholderText.length);
        }
      }
    }, 100);
  };

  return (
    <form className="chat-input-container" onSubmit={handleSubmit}>
      {showLargeContentHint && (
        <div className="content-hint">
          <span className="hint-icon">💡</span>
          <span>I can see you've pasted detailed content - I'll transform this into beautiful HTML!</span>
        </div>
      )}
      
      <div className="input-wrapper">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={handleMessageChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={isProcessing}
          className="chat-textarea"
          rows={1}
        />
        
        <button
          type="submit"
          disabled={!message.trim() || isProcessing}
          className="send-button"
          title="Send message (Ctrl/Cmd + Enter)"
        >
          {isProcessing ? (
            <div className="loading-spinner">⌛</div>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2,21L23,12L2,3V10L17,12L2,14V21Z" />
            </svg>
          )}
        </button>
      </div>
      
      <div className="input-footer">
        <div className="footer-left">
          <PromptLibraryButton 
            onClick={() => setIsModalOpen(true)}
            disabled={isProcessing}
          />
        </div>
        <div className="footer-right">
          <span className="char-count">{message.length.toLocaleString()} chars</span>
          <span className="help-text">Ctrl/Cmd + Enter to send</span>
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