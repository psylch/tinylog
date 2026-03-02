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

  useEffect(() => {
    setLoading(true);
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
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
          Dashboard
        </h1>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className="rounded-md px-3 py-1 text-xs font-medium transition-colors"
              style={{
                backgroundColor: period === p ? 'var(--accent-muted)' : 'transparent',
                color: period === p ? 'var(--accent)' : 'var(--text-muted)',
              }}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Stat cards */}
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
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
      <div className="mb-6 grid gap-6 lg:grid-cols-1">
        <ChartCard title="Sessions & Messages" loading={loading}>
          {daily.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={daily} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
                <YAxis yAxisId="left" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                <YAxis yAxisId="right" orientation="right" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg-elevated)',
                    borderColor: 'var(--border)',
                    borderRadius: 6,
                    fontSize: 12,
                    color: 'var(--text-primary)',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }} />
                <Line yAxisId="left" type="monotone" dataKey="sessions" stroke="var(--accent)" strokeWidth={2} dot={false} />
                <Line yAxisId="right" type="monotone" dataKey="messages" stroke="var(--text-muted)" strokeWidth={2} dot={false} strokeDasharray="5 5" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChart />
          )}
        </ChartCard>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Token Usage" loading={loading}>
          {daily.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={daily} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} tickFormatter={(v) => formatTokens(v)} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg-elevated)',
                    borderColor: 'var(--border)',
                    borderRadius: 6,
                    fontSize: 12,
                    color: 'var(--text-primary)',
                  }}
                  formatter={(v: number | undefined) => v != null ? formatTokens(v) : ''}
                />
                <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-secondary)' }} />
                <Area type="monotone" dataKey="input_tokens" stackId="1" fill="var(--accent-muted)" stroke="var(--accent)" name="Input" />
                <Area type="monotone" dataKey="output_tokens" stackId="1" fill="rgba(156,163,175,0.2)" stroke="var(--text-muted)" name="Output" />
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
                <XAxis type="number" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
                  width={75}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg-elevated)',
                    borderColor: 'var(--border)',
                    borderRadius: 6,
                    fontSize: 12,
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
    <div
      className="rounded-lg border p-4"
      style={{ backgroundColor: 'var(--bg-surface)', borderColor: 'var(--border)' }}
    >
      <h2 className="mb-4 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
        {title}
      </h2>
      {loading ? (
        <div className="skeleton h-64 w-full" />
      ) : (
        children
      )}
    </div>
  );
}

function EmptyChart({ message = 'No data available' }: { message?: string }) {
  return (
    <div className="flex h-64 items-center justify-center">
      <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
        {message}
      </p>
    </div>
  );
}
