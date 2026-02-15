import { useState, useEffect, useCallback } from 'react';
import { api } from '../../services/api';
import type { Version } from '../../types';
import VersionItem from './VersionItem';
import ConfirmDialog from '../ConfirmDialog/ConfirmDialog';
import './VersionTimeline.css';

interface VersionTimelineProps {
  documentId: string | null;
  onVersionPreview: (html: string) => void;
  onBackToCurrent: () => void;
  onRestoreVersion: (version: number) => void;
  isOpen: boolean;
  onToggle: () => void;
}

const VersionTimeline: React.FC<VersionTimelineProps> = ({
  documentId,
  onVersionPreview,
  onBackToCurrent,
  onRestoreVersion,
  isOpen,
  onToggle,
}) => {
  const [versions, setVersions] = useState<Version[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [restoreConfirm, setRestoreConfirm] = useState(false);
  const [diffMode, setDiffMode] = useState<'before' | 'after'>('after');
  const [beforeHtml, setBeforeHtml] = useState<string | null>(null);

  // Fetch versions when panel opens or document changes
  useEffect(() => {
    if (!isOpen || !documentId) {
      setVersions([]);
      setSelectedVersion(null);
      setDiffMode('after');
      setBeforeHtml(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .getVersions(documentId)
      .then(({ versions: v }) => {
        if (!cancelled) {
          setVersions(v);
          setSelectedVersion(null);
          setDiffMode('after');
          setBeforeHtml(null);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load versions');
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [isOpen, documentId]);

  const handleVersionClick = useCallback(
    async (ver: Version) => {
      if (!documentId) return;

      // If clicking the already-selected version, deselect and go back to current
      if (selectedVersion === ver.version) {
        setSelectedVersion(null);
        onBackToCurrent();
        return;
      }

      try {
        const detail = await api.getVersion(documentId, ver.version);
        setSelectedVersion(ver.version);
        onVersionPreview(detail.html_content);

        // Pre-fetch previous version for Before/After toggle
        if (ver.version > 1) {
          try {
            const prevDetail = await api.getVersion(documentId, ver.version - 1);
            setBeforeHtml(prevDetail.html_content);
          } catch {
            setBeforeHtml(null);
          }
        } else {
          setBeforeHtml(null);
        }
        setDiffMode('after');
      } catch {
        setError('Failed to load version');
      }
    },
    [documentId, selectedVersion, onVersionPreview, onBackToCurrent],
  );

  const handleBackToCurrent = useCallback(() => {
    setSelectedVersion(null);
    setDiffMode('after');
    setBeforeHtml(null);
    onBackToCurrent();
  }, [onBackToCurrent]);

  // Keyboard navigation for Before/After toggle
  useEffect(() => {
    if (selectedVersion === null) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft' && beforeHtml && selectedVersion > 1) {
        e.preventDefault();
        setDiffMode('before');
        onVersionPreview(beforeHtml);
      } else if (e.key === 'ArrowRight' && documentId && selectedVersion) {
        e.preventDefault();
        setDiffMode('after');
        api.getVersion(documentId, selectedVersion).then((detail) => {
          onVersionPreview(detail.html_content);
        });
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [selectedVersion, beforeHtml, documentId, onVersionPreview]);

  if (!isOpen) {
    return null;
  }

  const latestVersion = versions.length > 0 ? Math.max(...versions.map((v) => v.version)) : 0;

  return (
    <div className="version-timeline">
      <div className="version-timeline-header">
        <span className="version-timeline-title">Version History</span>
        <button className="version-timeline-close" onClick={onToggle} type="button">
          &times;
        </button>
      </div>

      {selectedVersion !== null && (
        <div className="version-preview-bar">
          <span>Viewing v{selectedVersion}</span>
          <div className="version-preview-actions">
            <div className="version-diff-toggle">
              <button
                className={`diff-toggle-btn${diffMode === 'before' ? ' active' : ''}`}
                onClick={() => {
                  setDiffMode('before');
                  if (beforeHtml) onVersionPreview(beforeHtml);
                }}
                disabled={!beforeHtml || selectedVersion <= 1}
                title={
                  selectedVersion <= 1
                    ? 'No previous version'
                    : `Show v${selectedVersion - 1}`
                }
                type="button"
              >
                ◀ Before
              </button>
              <button
                className={`diff-toggle-btn${diffMode === 'after' ? ' active' : ''}`}
                onClick={async () => {
                  setDiffMode('after');
                  if (documentId && selectedVersion) {
                    const detail = await api.getVersion(documentId, selectedVersion);
                    onVersionPreview(detail.html_content);
                  }
                }}
                type="button"
              >
                After ▶
              </button>
            </div>
            <button
              className="restore-version-btn"
              onClick={() => setRestoreConfirm(true)}
              type="button"
            >
              Restore this version
            </button>
            <button className="back-to-current-btn" onClick={handleBackToCurrent} type="button">
              Back to current
            </button>
          </div>
        </div>
      )}

      <div className="version-timeline-body">
        {loading ? (
          <div className="version-timeline-empty">Loading versions...</div>
        ) : error ? (
          <div className="version-timeline-error">{error}</div>
        ) : versions.length === 0 ? (
          <div className="version-timeline-empty">No versions yet</div>
        ) : (
          versions
            .slice()
            .sort((a, b) => b.version - a.version)
            .map((v) => (
              <VersionItem
                key={v.version}
                version={v}
                isLatest={v.version === latestVersion}
                isSelected={selectedVersion === v.version}
                onClick={() => handleVersionClick(v)}
              />
            ))
        )}
      </div>
      <ConfirmDialog
        isOpen={restoreConfirm}
        title={`Restore to Version ${selectedVersion}?`}
        message={`This will create a new version (v${latestVersion + 1}) with the content from v${selectedVersion}. Your current version will remain in history.`}
        onConfirm={() => {
          if (selectedVersion !== null) {
            onRestoreVersion(selectedVersion);
          }
        }}
        onCancel={() => setRestoreConfirm(false)}
        confirmText="Restore"
        cancelText="Cancel"
      />
    </div>
  );
};

export default VersionTimeline;
