import React, { useRef, useEffect } from 'react';
import './HtmlRenderer.css';

interface HtmlRendererProps {
  htmlContent: string;
  isFullscreen?: boolean;
}

const HtmlRenderer: React.FC<HtmlRendererProps> = ({ 
  htmlContent, 
  isFullscreen = false 
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    if (iframeRef.current) {
      const iframe = iframeRef.current;
      const doc = iframe.contentDocument || iframe.contentWindow?.document;
      
      if (doc) {
        doc.open();
        doc.write(htmlContent || `
          <!DOCTYPE html>
          <html>
          <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Preview</title>
            <style>
              body {
                font-family: 'Benton Sans', Arial, sans-serif;
                padding: 2rem;
                background: #f8f9fa;
                color: #333;
                text-align: center;
              }
              .placeholder {
                color: #6c757d;
                font-size: 1.1rem;
                margin: 2rem 0;
              }
              .icon {
                font-size: 3rem;
                margin-bottom: 1rem;
                opacity: 0.5;
              }
            </style>
          </head>
          <body>
            <div class="placeholder">
              <div class="icon">🎨</div>
              <p>Your HTML will appear here</p>
              <p>Start chatting to generate HTML content</p>
            </div>
          </body>
          </html>
        `);
        doc.close();
      }
    }
  }, [htmlContent]);

  return (
    <div className={`html-renderer ${isFullscreen ? 'fullscreen' : ''}`}>
      <iframe
        ref={iframeRef}
        title="HTML Preview"
        className="html-iframe"
        sandbox="allow-same-origin allow-scripts"
        loading="lazy"
      />
    </div>
  );
};

export default HtmlRenderer;