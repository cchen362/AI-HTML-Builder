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
📝 Templates
    </button>
  );
};

export default PromptLibraryButton;