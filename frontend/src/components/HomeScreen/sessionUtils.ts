/** Parse a SQLite UTC timestamp (which lacks 'Z' suffix) as UTC. */
function parseUTC(dateStr: string): number {
  return new Date(dateStr.endsWith('Z') ? dateStr : dateStr + 'Z').getTime();
}

/** Force UTC interpretation for Date object construction. */
function toUTCDate(dateStr: string): Date {
  return new Date(dateStr.endsWith('Z') ? dateStr : dateStr + 'Z');
}

/** Format a date string as a relative time (e.g., "2 hours ago"). */
export function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = parseUTC(dateStr);
  const diffMs = now - then;
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 60) return 'just now';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin} min ago`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}h ago`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 7) return `${diffDay}d ago`;
  const diffWeek = Math.floor(diffDay / 7);
  if (diffWeek < 5) return `${diffWeek}w ago`;
  return toUTCDate(dateStr).toLocaleDateString();
}

/** Calculate days until session expires (30 days after last_active). */
export function daysUntilExpiry(lastActive: string): number {
  const expiresAt = parseUTC(lastActive) + 30 * 86400000;
  return Math.ceil((expiresAt - Date.now()) / 86400000);
}

/** Get CSS variable for expiry color based on days remaining. */
export function expiryColor(daysLeft: number): string {
  if (daysLeft > 14) return 'var(--signal-success)';
  if (daysLeft > 7) return 'var(--accent-primary)';
  return 'var(--signal-error)';
}
