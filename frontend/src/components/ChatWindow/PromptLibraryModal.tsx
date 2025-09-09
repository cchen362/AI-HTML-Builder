import React, { useState, useEffect } from 'react';
import type { PromptTemplate } from '../../data/promptTemplates';
import { getTemplatesByCategory } from '../../data/promptTemplates';
import './PromptLibraryModal.css';

interface PromptLibraryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectTemplate: (template: PromptTemplate) => void;
}

const PromptLibraryModal: React.FC<PromptLibraryModalProps> = ({
  isOpen,
  onClose,
  onSelectTemplate
}) => {
  const [selectedTemplate, setSelectedTemplate] = useState<PromptTemplate | null>(null);
  const [categories] = useState(() => getTemplatesByCategory());

  // Close modal on Escape key
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  const handleBackdropClick = (event: React.MouseEvent) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  const handleUseTemplate = () => {
    if (selectedTemplate) {
      onSelectTemplate(selectedTemplate);
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="prompt-library-overlay" onClick={handleBackdropClick}>
      <div className="prompt-library-modal">
        <div className="modal-header">
          <h2>Prompt Template Library</h2>
          <button 
            className="close-button" 
            onClick={onClose}
            aria-label="Close modal"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>

        <div className="modal-content">
          <div className="templates-sidebar">
            <p className="sidebar-description">
              Choose a template that fits your content style:
            </p>
            
            {Array.from(categories.entries()).map(([category, templates]) => (
              <div key={category} className="category-group">
                <h3 className="category-title">{category}</h3>
                {templates.map((template) => (
                  <button
                    key={template.id}
                    className={`template-item ${selectedTemplate?.id === template.id ? 'active' : ''}`}
                    onClick={() => setSelectedTemplate(template)}
                  >
                    <div className="template-name">{template.name}</div>
                    <div className="template-description">{template.description}</div>
                  </button>
                ))}
              </div>
            ))}
          </div>

          <div className="template-preview">
            {selectedTemplate ? (
              <div className="preview-content">
                <div className="preview-header">
                  <h3>{selectedTemplate.name}</h3>
                  <span className="template-category">{selectedTemplate.category}</span>
                </div>
                
                <p className="template-full-description">
                  {selectedTemplate.description}
                </p>
                
                <div className="template-preview-text">
                  <h4>Template Preview:</h4>
                  <div className="template-text">
                    {selectedTemplate.template
                      .replace('{USER_CONTENT}', '[Your content will be inserted here]')
                      .split('\n')
                      .map((line, index) => (
                        <div key={index} className={
                          line.startsWith('DESIGN REQUIREMENTS:') || 
                          line.startsWith('CONTENT TO INCLUDE:') || 
                          line.startsWith('STRUCTURE REQUIREMENTS:') ||
                          line.startsWith('FEATURES REQUIRED:') ||
                          line.startsWith('INTERACTIVE FEATURES:') ||
                          line.startsWith('REPORT SECTIONS:') ||
                          line.startsWith('WORKFLOW FEATURES:') 
                            ? 'section-header' : 'template-line'
                        }>
                          {line}
                        </div>
                      ))
                    }
                  </div>
                </div>
                
                <div className="preview-actions">
                  <button 
                    className="use-template-button"
                    onClick={handleUseTemplate}
                  >
                    Use This Template
                  </button>
                </div>
              </div>
            ) : (
              <div className="preview-placeholder">
                <div className="placeholder-content">
                  <svg width="64" height="64" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
                  </svg>
                  <h3>Select a Template</h3>
                  <p>Choose a template from the left to see its preview and details.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PromptLibraryModal;