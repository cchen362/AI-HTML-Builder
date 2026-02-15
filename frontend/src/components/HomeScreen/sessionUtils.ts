/** Format a date string as a relative time (e.g., "2 hours ago"). */
export function relativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
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
  return new Date(dateStr).toLocaleDateString();
}

/** Calculate days until session expires (30 days after last_active). */
export function daysUntilExpiry(lastActive: string): number {
  const expiresAt = new Date(lastActive).getTime() + 30 * 86400000;
  return Math.ceil((expiresAt - Date.now()) / 86400000);
}
