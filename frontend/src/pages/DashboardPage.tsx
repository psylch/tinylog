import { useEffect, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  AreaChart, Area,
  BarChart, Bar, Cell,
} from 'recharts';
import StatCard from '../components/StatCard';
import { getOverview, getDailyMetrics, getToolStats } from '../services/api';
import type { OverviewStats, DailyMetrics } from '../types';
import { formatTokens, getPeriodDates } from '../utils';

const PERIODS = ['today', '7d', '30d', 'all'] as const;

const TOOL_COLORS = [
  '#D4AF37', '#22c55e', '#3b82f6', '#ef4444', '#f59e0b', '#8b5cf6',
  '#ec4899', '#14b8a6', '#f97316', '#6366f1',
];

export default function DashboardPage() {
  const [period, setPeriod] = useState<string>('7d');
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [daily, setDaily] = useState<DailyMetrics[]>([]);
  const [toolStats, setToolStats] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const { from, to } = getPeriodDates(period);
    Promise.all([
      getOverview(period),
      getDailyMetrics(from, to),
      getToolStats(from, to),
    ])
      .then(([ov, d, t]) => {
        setOverview(ov);
        setDaily(d.data);
        setToolStats(t.summary || {});
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
      })
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between" style={{ marginBottom: '1.5rem' }}>
        <h1 className="text-xl font-semibold text-primary">Dashboard</h1>
        <div
          className="flex gap-1"
          style={{
            backgroundColor: 'var(--bg-hover)',
            padding: '0.25rem',
            borderRadius: '0.5rem',
          }}
        >
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              style={{
                backgroundColor: period === p ? 'var(--bg-surface)' : 'transparent',
                color: period === p ? 'var(--text-primary)' : 'var(--text-muted)',
                boxShadow: period === p ? 'var(--shadow-sm)' : 'none',
                padding: '0.25rem 0.75rem',
                borderRadius: '0.375rem',
                fontSize: '0.75rem',
                fontWeight: 500,
                transition: 'all 0.2s',
                cursor: 'pointer',
                border: 'none',
              }}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="notice" style={{ marginBottom: '1.5rem' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span className="flex-1">{error}</span>
          <button
            onClick={() => setError(null)}
            style={{ opacity: 0.6, cursor: 'pointer', transition: 'opacity 0.2s', border: 'none', background: 'none', color: 'inherit' }}
            onMouseEnter={e => e.currentTarget.style.opacity = '1'}
            onMouseLeave={e => e.currentTarget.style.opacity = '0.6'}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid-4" style={{ marginBottom: '1.5rem' }}>
        <StatCard
          label="Sessions"
          value={overview ? String(overview.current.sessions) : '-'}
          trend={overview?.trends.sessions}
          loading={loading}
        />
        <StatCard
          label="Messages"
          value={overview ? String(overview.current.messages) : '-'}
          trend={overview?.trends.messages}
          loading={loading}
        />
        <StatCard
          label="Tokens"
          value={overview ? formatTokens(overview.current.total_tokens) : '-'}
          trend={overview?.trends.total_tokens}
          loading={loading}
        />
        <StatCard
          label="Avg TTFT"
          value={overview ? (overview.current.avg_ttft?.toFixed(1) ?? '-') + 's' : '-'}
          trend={overview?.trends.avg_ttft}
          loading={loading}
        />
      </div>

      {/* Charts */}
      <div style={{ marginBottom: '1.5rem' }}>
        <ChartCard title="Sessions & Messages" loading={loading}>
          {daily.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={daily} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={(v) => v.slice(5)} axisLine={false} tickLine={false} dy={10} />
                <YAxis yAxisId="left" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} dx={-10} />
                <YAxis yAxisId="right" orientation="right" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} dx={10} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    boxShadow: 'var(--shadow-md)',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: 'var(--text-primary)',
                  }}
                  itemStyle={{ color: 'var(--text-primary)' }}
                />
                <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: '10px' }} />
                <Line yAxisId="left" type="monotone" dataKey="sessions" stroke="var(--accent)" strokeWidth={2} dot={{ r: 3, fill: 'var(--bg-surface)', strokeWidth: 2 }} activeDot={{ r: 5, fill: 'var(--accent)', stroke: 'var(--bg-surface)', strokeWidth: 2 }} />
                <Line yAxisId="right" type="monotone" dataKey="messages" stroke="var(--text-secondary)" strokeWidth={2} dot={{ r: 3, fill: 'var(--bg-surface)', strokeWidth: 2 }} strokeDasharray="4 4" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChart />
          )}
        </ChartCard>
      </div>

      <div className="grid-2">
        <ChartCard title="Token Usage" loading={loading}>
          {daily.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={daily} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <defs>
                  <linearGradient id="colorInput" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent)" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="var(--accent)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={(v) => v.slice(5)} axisLine={false} tickLine={false} dy={10} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={(v) => formatTokens(v)} axisLine={false} tickLine={false} dx={-10} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    boxShadow: 'var(--shadow-md)',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: 'var(--text-primary)',
                  }}
                  formatter={(v: number | undefined) => v != null ? formatTokens(v) : ''}
                />
                <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: '10px' }} />
                <Area type="monotone" dataKey="input_tokens" stackId="1" fill="url(#colorInput)" stroke="var(--accent)" strokeWidth={2} name="Input" activeDot={{ r: 5, fill: 'var(--accent)', stroke: 'var(--bg-surface)', strokeWidth: 2 }} />
                <Area type="monotone" dataKey="output_tokens" stackId="1" fill="var(--bg-hover-strong)" stroke="var(--text-muted)" strokeWidth={2} name="Output" activeDot={{ r: 5, fill: 'var(--text-muted)', stroke: 'var(--bg-surface)', strokeWidth: 2 }} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChart />
          )}
        </ChartCard>

        <ChartCard title="Tool Calls" loading={loading}>
          {Object.keys(toolStats).length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={Object.entries(toolStats).map(([name, count]) => ({ name, count }))}
                layout="vertical"
                margin={{ top: 5, right: 20, bottom: 5, left: 80 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} dy={10} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fill: 'var(--text-secondary)', fontSize: 11 }}
                  width={75}
                  axisLine={false}
                  tickLine={false}
                  dx={-10}
                />
                <Tooltip
                  cursor={{ fill: 'var(--bg-hover)' }}
                  contentStyle={{
                    backgroundColor: 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    boxShadow: 'var(--shadow-md)',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: 'var(--text-primary)',
                  }}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} maxBarSize={24}>
                  {Object.keys(toolStats).map((_, i) => (
                    <Cell key={i} fill={TOOL_COLORS[i % TOOL_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChart message="No tool calls in this period" />
          )}
        </ChartCard>
      </div>
    </div>
  );
}

function ChartCard({ title, loading, children }: { title: string; loading: boolean; children: React.ReactNode }) {
  return (
    <div className="card" style={{ padding: '1.25rem', height: '100%' }}>
      <h2 className="text-sm font-semibold text-secondary" style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        {title}
      </h2>
      {loading ? (
        <div className="skeleton" style={{ height: '280px', width: '100%' }} />
      ) : (
        children
      )}
    </div>
  );
}

function EmptyChart({ message = 'No data available' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3" style={{ height: '280px' }}>
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.3 }}>
        <line x1="18" y1="20" x2="18" y2="10" />
        <line x1="12" y1="20" x2="12" y2="4" />
        <line x1="6" y1="20" x2="6" y2="14" />
      </svg>
      <p className="text-sm text-muted">{message}</p>
    </div>
  );
}
