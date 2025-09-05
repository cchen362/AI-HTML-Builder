import React, { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import './ChatInput.css';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isProcessing?: boolean;
  placeholder?: string;
}

const ChatInput: React.FC<ChatInputProps> = ({ 
  onSendMessage, 
  isProcessing = false,
  placeholder = "Tell me what kind of website, page, or content you'd like to create. Be as detailed or creative as you want - I'll design something professional and polished for you!"
}) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isProcessing) {
      onSendMessage(message.trim());
      setMessage('');
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  // Auto-resize textarea based on content
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const maxHeight = Math.min(textarea.scrollHeight, window.innerHeight * 0.4); // 40% max height
      textarea.style.height = `${Math.max(maxHeight, 120)}px`; // 120px minimum
    }
  }, [message]);

  const handleKeyPress = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form 
      className="chat-input"
      onSubmit={handleSubmit}
    >
      <div className="input-container">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder={placeholder}
          disabled={isProcessing}
          className="message-input expandable"
        />
        
        <div className="input-actions">
          <button
            type="submit"
            disabled={!message.trim() || isProcessing}
            className="send-button"
            title="Send message (Ctrl+Enter)"
          >
            {isProcessing ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" className="animate-spin">
                <path d="M12,4V2A10,10 0 0,0 2,12H4A8,8 0 0,1 12,4Z" />
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2,21L23,12L2,3V10L17,12L2,14V21Z" />
              </svg>
            )}
          </button>
        </div>
      </div>

      <div className="input-help">
        <span>✨ Try: "Create a landing page for my photography business" or paste your content to style</span>
        <span>•</span>
        <span>Ctrl+Enter to send</span>
      </div>
    </form>
  );
};

export default ChatInput;