interface StatCardProps {
  label: string;
  value: string;
  trend?: number;
  loading?: boolean;
}

export default function StatCard({ label, value, trend, loading }: StatCardProps) {
  if (loading) {
    return (
      <div
        className="rounded-lg border p-4"
        style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}
      >
        <div className="skeleton mb-2 h-3 w-16" />
        <div className="skeleton mb-1 h-7 w-20" />
        <div className="skeleton h-3 w-12" />
      </div>
    );
  }

  const hasTrend = trend != null && trend !== 0;
  const trendColor = !hasTrend
    ? 'var(--text-muted)'
    : trend! > 0
      ? 'var(--success)'
      : 'var(--danger)';

  const trendIcon = !hasTrend
    ? '~'
    : trend! > 0
      ? String.fromCharCode(8593) // up arrow
      : String.fromCharCode(8595); // down arrow

  return (
    <div
      className="rounded-lg border p-4 transition-colors"
      style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
    >
      <p className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
        {label}
      </p>
      <p className="mt-1 text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>
        {value}
      </p>
      {trend != null && (
        <p className="mt-1 text-xs font-medium" style={{ color: trendColor }}>
          {trendIcon} {Math.abs(trend).toFixed(1)}%
        </p>
      )}
    </div>
  );
}
