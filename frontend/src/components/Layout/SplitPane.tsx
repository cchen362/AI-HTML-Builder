import React, { useState, useRef, useCallback } from 'react';
import './SplitPane.css';

interface SplitPaneProps {
  leftContent: React.ReactNode;
  rightContent: React.ReactNode;
  defaultPosition?: number;
  minSize?: number;
  maxSize?: number;
}

const SplitPane: React.FC<SplitPaneProps> = ({
  leftContent,
  rightContent,
  defaultPosition = 50,
  minSize = 20,
  maxSize = 80
}) => {
  const [splitPosition, setSplitPosition] = useState(defaultPosition);
  const [isDragging, setIsDragging] = useState(false);
  const splitPaneRef = useRef<HTMLDivElement>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!splitPaneRef.current) return;
    
    setIsDragging(true);
    
    // Store initial values
    const startX = e.clientX;
    const startPosition = splitPosition;
    const containerRect = splitPaneRef.current.getBoundingClientRect();
    
    const handleMouseMove = (e: MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      
      if (!splitPaneRef.current) return;
      
      // Calculate position based on mouse movement from start
      const deltaX = e.clientX - startX;
      const deltaPercent = (deltaX / containerRect.width) * 100;
      const newPosition = startPosition + deltaPercent;
      const clampedPosition = Math.max(minSize, Math.min(maxSize, newPosition));
      setSplitPosition(clampedPosition);
    };
    
    const handleMouseUp = (e: MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      
      setIsDragging(false);
      document.removeEventListener('mousemove', handleMouseMove, { capture: true });
      document.removeEventListener('mouseup', handleMouseUp, { capture: true });
      
      // Reset body styles
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      document.body.style.pointerEvents = '';
      
      // Reset selection
      if (window.getSelection) {
        window.getSelection()?.removeAllRanges();
      }
    };
    
    // Use capture phase and explicit options to prevent content from interfering
    document.addEventListener('mousemove', handleMouseMove, { capture: true, passive: false });
    document.addEventListener('mouseup', handleMouseUp, { capture: true, passive: false });
    
    // Set body styles to prevent interference
    document.body.style.cursor = 'ew-resize';
    document.body.style.userSelect = 'none';
    document.body.style.pointerEvents = 'none';
  }, [minSize, maxSize, splitPosition]);

  return (
    <div ref={splitPaneRef} className={`split-pane ${isDragging ? 'dragging' : ''}`}>
      {/* Overlay during dragging to prevent content interference */}
      {isDragging && <div className="split-pane-overlay" />}
      
      <div 
        className={`split-pane-left ${isDragging ? 'dragging' : ''}`}
        style={{ width: `${splitPosition}%` }}
      >
        {leftContent}
      </div>
      
      <div 
        className={`split-pane-divider ${isDragging ? 'dragging' : ''}`}
        onMouseDown={handleMouseDown}
      >
        <div className="divider-handle">
          <div className="divider-dots">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>
      
      <div 
        className={`split-pane-right ${isDragging ? 'dragging' : ''}`}
        style={{ width: `${100 - splitPosition}%` }}
      >
        {rightContent}
      </div>
    </div>
  );
};

export default SplitPane;