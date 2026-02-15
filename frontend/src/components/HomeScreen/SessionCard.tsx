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
      <div className="session-card-title">{session.title}</div>
      <div className="session-card-meta">
        <span>{session.doc_count} {session.doc_count === 1 ? 'doc' : 'docs'}</span>
        <span className="session-card-dot">&middot;</span>
        <span>{timeAgo}</span>
      </div>
      <div
        className="session-card-expiry"
        style={{ color: expiryColor(daysLeft) }}
      >
        {daysLeft > 0
          ? `Expires in ${daysLeft} day${daysLeft !== 1 ? 's' : ''}`
          : 'Expired'}
      </div>
    </button>
  );
};

export default SessionCard;
