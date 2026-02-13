import React from 'react';
import type { Version } from '../../types';

interface VersionItemProps {
  version: Version;
  isLatest: boolean;
  isSelected: boolean;
  onClick: () => void;
}

const MODEL_LABELS: Record<string, string> = {
  'claude-sonnet-4-20250514': 'Claude',
  'gemini-2.5-pro': 'Gemini',
  'svg-template': 'SVG',
};

function formatModel(model: string): string {
  return MODEL_LABELS[model] || model.split('-')[0] || model;
}

function formatTime(created_at: string): string {
  return new Date(created_at).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });
}

const VersionItem: React.FC<VersionItemProps> = ({
  version,
  isLatest,
  isSelected,
  onClick,
}) => {
  const classes = [
    'version-item',
    isSelected ? 'version-item--selected' : '',
    isLatest ? 'version-item--current' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button className={classes} onClick={onClick} type="button">
      <div className="version-item-header">
        <span className="version-number">v{version.version}</span>
        {isLatest && <span className="version-badge version-badge--current">Current</span>}
        <span className="version-model">{formatModel(version.model_used)}</span>
      </div>
      <div className="version-summary">{version.edit_summary}</div>
      {version.user_prompt && (
        <div className="version-prompt" title={version.user_prompt}>
          {version.user_prompt.length > 60
            ? version.user_prompt.slice(0, 60) + '…'
            : version.user_prompt}
        </div>
      )}
      <div className="version-time">{formatTime(version.created_at)}</div>
    </button>
  );
};

export default VersionItem;
