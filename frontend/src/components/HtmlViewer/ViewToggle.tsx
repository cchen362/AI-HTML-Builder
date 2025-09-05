import React from 'react';
import './ViewToggle.css';

interface ViewToggleProps {
  viewMode: 'rendered' | 'code';
  onToggle: (mode: 'rendered' | 'code') => void;
  onFullscreen?: () => void;
  onNewTab?: () => void;
  onExport?: () => void;
  isFullscreen?: boolean;
  htmlContent?: string;
}

const ViewToggle: React.FC<ViewToggleProps> = ({
  viewMode,
  onToggle,
  onExport,
  htmlContent = ""
}) => {
  const handleOpenNewTab = () => {
    if (htmlContent) {
      const blob = new Blob([htmlContent], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      window.open(url, '_blank', 'noopener,noreferrer');
      // Clean up the blob URL after a delay
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }
  };
  return (
    <div className="view-toggle">
      <div className="toggle-buttons">
        <button
          className={`toggle-btn ${viewMode === 'rendered' ? 'active' : ''}`}
          onClick={() => onToggle('rendered')}
          title="Preview rendered HTML"
        >
          👁️ Preview
        </button>
        <button
          className={`toggle-btn ${viewMode === 'code' ? 'active' : ''}`}
          onClick={() => onToggle('code')}
          title="View HTML source code"
        >
          📝 Code
        </button>
      </div>

      <div className="action-buttons">
        {htmlContent && (
          <button
            className="action-btn fullscreen"
            onClick={handleOpenNewTab}
            title="Open in new tab"
          >
            🔗 Full Screen
          </button>
        )}
        
        {onExport && (
          <button
            className="action-btn export"
            onClick={onExport}
            title="Export HTML file"
          >
            💾 Export
          </button>
        )}
      </div>
    </div>
  );
};

export default ViewToggle;