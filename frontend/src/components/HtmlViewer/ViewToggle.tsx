import React from 'react';
import './ViewToggle.css';

interface ViewToggleProps {
  viewMode: 'rendered' | 'code';
  onToggle: (mode: 'rendered' | 'code') => void;
  onFullscreen?: () => void;
  onExport?: () => void;
  isFullscreen?: boolean;
}

const ViewToggle: React.FC<ViewToggleProps> = ({
  viewMode,
  onToggle,
  onFullscreen,
  onExport,
  isFullscreen = false
}) => {
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
        {onFullscreen && (
          <button
            className="action-btn"
            onClick={onFullscreen}
            title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          >
            {isFullscreen ? '🗗' : '🗖'}
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