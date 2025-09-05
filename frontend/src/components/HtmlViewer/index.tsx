import React, { useState, useCallback } from 'react';
import HtmlRenderer from './HtmlRenderer';
import CodeEditor from './CodeEditor';
import ViewToggle from './ViewToggle';
import './HtmlViewer.css';

interface HtmlViewerProps {
  htmlContent: string;
  onContentEdit?: (content: string) => void;
  onExport?: () => void;
}

const HtmlViewer: React.FC<HtmlViewerProps> = ({
  htmlContent,
  onContentEdit,
  onExport
}) => {
  const [viewMode, setViewMode] = useState<'rendered' | 'code'>('rendered');
  const [isFullscreen, setIsFullscreen] = useState(false);

  const handleToggle = useCallback((mode: 'rendered' | 'code') => {
    setViewMode(mode);
  }, []);

  const handleFullscreen = useCallback(() => {
    setIsFullscreen(prev => !prev);
  }, []);

  const handleContentChange = useCallback((content: string) => {
    if (onContentEdit) {
      onContentEdit(content);
    }
  }, [onContentEdit]);

  return (
    <div className={`html-viewer ${isFullscreen ? 'fullscreen' : ''}`}>
      <ViewToggle
        viewMode={viewMode}
        onToggle={handleToggle}
        onFullscreen={handleFullscreen}
        onExport={onExport}
        isFullscreen={isFullscreen}
        htmlContent={htmlContent}
      />

      <div className="viewer-content">
        {viewMode === 'rendered' ? (
          <HtmlRenderer 
            htmlContent={htmlContent}
            isFullscreen={isFullscreen}
          />
        ) : (
          <CodeEditor
            htmlContent={htmlContent}
            onContentChange={handleContentChange}
            readOnly={false}
          />
        )}
      </div>

      {isFullscreen && (
        <div className="fullscreen-overlay" onClick={handleFullscreen} />
      )}
    </div>
  );
};

export default HtmlViewer;