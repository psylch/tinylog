interface StatCardProps {
  label: string;
  value: string;
  trend?: number;
  loading?: boolean;
}

export default function StatCard({ label, value, trend, loading }: StatCardProps) {
  if (loading) {
    return (
      <div className="card" style={{ padding: '1.25rem' }}>
        <div className="skeleton" style={{ height: '0.75rem', width: '4rem', marginBottom: '0.75rem' }} />
        <div className="skeleton" style={{ height: '1.75rem', width: '5rem', marginBottom: '0.5rem' }} />
        <div className="skeleton" style={{ height: '0.75rem', width: '3rem' }} />
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
      ? String.fromCharCode(8593)
      : String.fromCharCode(8595);

  return (
    <div className="card" style={{ padding: '1.25rem' }}>
      <p className="text-secondary" style={{ fontSize: '0.6875rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </p>
      <p className="text-primary" style={{ marginTop: '0.5rem', fontSize: '1.5rem', fontWeight: 600, letterSpacing: '-0.02em' }}>
        {value}
      </p>
      {trend != null && (
        <p style={{ marginTop: '0.375rem', fontSize: '0.75rem', fontWeight: 500, color: trendColor }}>
          {trendIcon} {Math.abs(trend).toFixed(1)}%
        </p>
      )}
    </div>
  );
}
