import React from 'react';
import './CodeEditor.css';

interface CodeEditorProps {
  htmlContent: string;
  onContentChange?: (content: string) => void;
  readOnly?: boolean;
}

const CodeEditor: React.FC<CodeEditorProps> = ({ 
  htmlContent, 
  onContentChange,
  readOnly = true 
}) => {
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (!readOnly && onContentChange) {
      onContentChange(e.target.value);
    }
  };

  const placeholderContent = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated HTML</title>
    <style>
        /* Your CSS will appear here */
        body {
            font-family: 'Benton Sans', Arial, sans-serif;
            margin: 0;
            padding: 2rem;
            background: #f8f9fa;
        }
    </style>
</head>
<body>
    <!-- Your HTML content will appear here -->
    <h1>AI-Generated HTML</h1>
    <p>Start chatting to see generated HTML code</p>
</body>
</html>`;

  const displayContent = htmlContent || placeholderContent;
  const lineCount = displayContent.split('\n').length;

  return (
    <div className="code-editor">
      <div className="code-header">
        <div className="code-title">
          <span className="file-icon">📄</span>
          generated.html
        </div>
        <div className="code-stats">
          {lineCount} lines • {displayContent.length} chars
        </div>
      </div>
      
      <div className="code-content">
        <div className="line-numbers">
          {Array.from({ length: lineCount }, (_, i) => (
            <div key={i + 1} className="line-number">
              {i + 1}
            </div>
          ))}
        </div>
        
        <textarea
          value={displayContent}
          onChange={handleChange}
          readOnly={readOnly}
          className={`code-textarea ${readOnly ? 'read-only' : 'editable'}`}
          spellCheck={false}
          wrap="off"
        />
      </div>
    </div>
  );
};

export default CodeEditor;