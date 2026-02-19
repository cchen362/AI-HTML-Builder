import type { SessionSummary } from '../../types';

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

// ---------------------------------------------------------------------------
// Time grouping for card grid (Plan 023 Phase 3)
// ---------------------------------------------------------------------------

export type TimeGroup = 'Today' | 'This Week' | 'This Month' | 'Earlier';

/** Determine which time group a session belongs to. */
export function getTimeGroup(dateStr: string): TimeGroup {
  const now = new Date();
  const then = toUTCDate(dateStr);

  // Today: same calendar date (local timezone)
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (then >= todayStart) return 'Today';

  // This Week: within last 7 calendar days
  const weekAgo = new Date(todayStart.getTime() - 6 * 86400000);
  if (then >= weekAgo) return 'This Week';

  // This Month: same calendar month
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  if (then >= monthStart) return 'This Month';

  return 'Earlier';
}

/** Group sessions by time period, preserving order within each group. */
export function groupSessionsByTime(
  sessions: SessionSummary[]
): Map<TimeGroup, SessionSummary[]> {
  const groupMap = new Map<TimeGroup, SessionSummary[]>();
  const order: TimeGroup[] = ['Today', 'This Week', 'This Month', 'Earlier'];

  for (const session of sessions) {
    const group = getTimeGroup(session.last_active);
    if (!groupMap.has(group)) {
      groupMap.set(group, []);
    }
    groupMap.get(group)!.push(session);
  }

  // Return in chronological order, omitting empty groups
  const result = new Map<TimeGroup, SessionSummary[]>();
  for (const key of order) {
    const items = groupMap.get(key);
    if (items && items.length > 0) {
      result.set(key, items);
    }
  }
  return result;
}
