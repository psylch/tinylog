export function formatTokens(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(n >= 10_000 ? 0 : 1) + 'K';
  return String(n);
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return seconds.toFixed(1) + 's';
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

export function relativeTime(ts: number): string {
  const now = Date.now() / 1000;
  const diff = now - ts;
  if (diff < 60) return 'just now';
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  if (diff < 604800) return Math.floor(diff / 86400) + 'd ago';
  return new Date(ts * 1000).toLocaleDateString();
}

export function shortSessionId(id: string): string {
  return id.length > 8 ? id.slice(0, 8) : id;
}

export function formatDate(ts: number): string {
  return new Date(ts * 1000).toLocaleDateString('en-CA'); // YYYY-MM-DD
}

export function getPeriodDates(period: string): { from: string; to: string } {
  const now = new Date();
  const to = now.toISOString().slice(0, 10);
  let from: string;

  switch (period) {
    case 'today':
      from = to;
      break;
    case '7d':
      from = new Date(now.getTime() - 7 * 86400000).toISOString().slice(0, 10);
      break;
    case '30d':
      from = new Date(now.getTime() - 30 * 86400000).toISOString().slice(0, 10);
      break;
    default: // 'all'
      from = '2020-01-01';
      break;
  }

  return { from, to };
}
