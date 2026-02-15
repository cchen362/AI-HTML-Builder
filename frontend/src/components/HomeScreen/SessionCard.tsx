import React from 'react';
import type { SessionSummary } from '../../types';
import { relativeTime, daysUntilExpiry, expiryColor } from './sessionUtils';

interface SessionCardProps {
  session: SessionSummary;
  onClick: () => void;
  style?: React.CSSProperties;
}

const SessionCard: React.FC<SessionCardProps> = ({ session, onClick, style }) => {
  const daysLeft = daysUntilExpiry(session.last_active);
  const timeAgo = relativeTime(session.last_active);

  return (
    <button
      type="button"
      className="session-card"
      onClick={onClick}
      style={style}
    >
      <span className="session-card-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
        </svg>
      </span>
      <div className="session-card-title">{session.title}</div>
      <div className="session-card-meta">
        <span>{session.doc_count} {session.doc_count === 1 ? 'doc' : 'docs'}</span>
        <span>&middot;</span>
        <span>{timeAgo}</span>
        <span>&middot;</span>
        <span style={{ color: expiryColor(daysLeft) }}>{daysLeft}d</span>
      </div>
    </button>
  );
};

export default SessionCard;
