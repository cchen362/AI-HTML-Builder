import React from 'react';
import './PromptLibraryButton.css';

interface PromptLibraryButtonProps {
  onClick: () => void;
  disabled?: boolean;
}

const PromptLibraryButton: React.FC<PromptLibraryButtonProps> = ({ 
  onClick, 
  disabled = false 
}) => {
  return (
    <button
      className="prompt-library-button"
      onClick={onClick}
      disabled={disabled}
      title="Browse prompt templates"
      type="button"
    >
      <svg 
        width="16" 
        height="16" 
        viewBox="0 0 24 24" 
        fill="currentColor"
        className="template-icon"
      >
        <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
      </svg>
      Templates
    </button>
  );
};

export default PromptLibraryButton;