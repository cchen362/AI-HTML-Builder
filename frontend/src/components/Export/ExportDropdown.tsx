import { useState, useRef, useEffect } from 'react';
import { api } from '../../services/api';
import { humanizeError } from '../../utils/errorUtils';
import './ExportDropdown.css';

interface ExportDropdownProps {
  onExportHtml: () => void;
  disabled?: boolean;
  documentId: string | null;
  documentTitle?: string;
  isInfographic?: boolean;
}

type ExportFormat = 'pptx' | 'pdf' | 'png';

const ExportDropdown: React.FC<ExportDropdownProps> = ({
  onExportHtml,
  disabled = false,
  documentId,
  documentTitle,
  isInfographic = false,
}) => {
  const [open, setOpen] = useState(false);
  const [loadingFormat, setLoadingFormat] = useState<ExportFormat | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [successFormat, setSuccessFormat] = useState<ExportFormat | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  // Auto-dismiss error after 5 seconds
  useEffect(() => {
    if (!exportError) return;
    const timer = setTimeout(() => setExportError(null), 5000);
    return () => clearTimeout(timer);
  }, [exportError]);

  const handleExport = async (format: ExportFormat) => {
    if (!documentId || loadingFormat) return;
    setLoadingFormat(format);
    setExportError(null);
    setSuccessFormat(null);
    try {
      await api.exportDocument(documentId, format, documentTitle);
      setLoadingFormat(null);
      setSuccessFormat(format);
      setTimeout(() => {
        setSuccessFormat(null);
        setOpen(false);
      }, 2000);
    } catch (err) {
      setLoadingFormat(null);
      setExportError(humanizeError(err));
    }
  };

  return (
    <div className="export-dropdown" ref={ref}>
      <button
        className="export-btn"
        onClick={() => setOpen((v) => !v)}
        disabled={disabled}
      >
        Export
      </button>
      {open && (
        <div className="export-dropdown-menu">
          {exportError && (
            <div className="export-error">
              <span>{exportError}</span>
              <button type="button" onClick={() => setExportError(null)}>&times;</button>
            </div>
          )}
          {!isInfographic && (
            <button
              className="export-dropdown-item"
              onClick={() => {
                onExportHtml();
                setOpen(false);
              }}
            >
              HTML
            </button>
          )}
          {!isInfographic && (
            <button
              className="export-dropdown-item"
              onClick={() => handleExport('pptx')}
              disabled={!documentId || loadingFormat === 'pptx'}
            >
              {loadingFormat === 'pptx' ? (
                <span className="export-loading"><span className="export-spinner" /> Exporting PowerPoint...</span>
              ) : successFormat === 'pptx' ? (
                <span className="export-success">PowerPoint downloaded!</span>
              ) : (
                'PowerPoint'
              )}
            </button>
          )}
          {!isInfographic && (
            <button
              className="export-dropdown-item"
              onClick={() => handleExport('pdf')}
              disabled={!documentId || loadingFormat === 'pdf'}
            >
              {loadingFormat === 'pdf' ? (
                <span className="export-loading"><span className="export-spinner" /> Exporting PDF...</span>
              ) : successFormat === 'pdf' ? (
                <span className="export-success">PDF downloaded!</span>
              ) : (
                'PDF'
              )}
            </button>
          )}
          <button
            className="export-dropdown-item"
            onClick={() => handleExport('png')}
            disabled={!documentId || loadingFormat === 'png'}
          >
            {loadingFormat === 'png' ? (
              <span className="export-loading"><span className="export-spinner" /> Exporting PNG...</span>
            ) : successFormat === 'png' ? (
              <span className="export-success">PNG downloaded!</span>
            ) : (
              'Image (PNG)'
            )}
          </button>
          {isInfographic && (
            <div className="export-infographic-hint">
              Infographics can only be exported as PNG
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ExportDropdown;
