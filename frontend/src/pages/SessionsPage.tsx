import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getSessions } from '../services/api';
import type { PaginatedResponse, SessionSummary } from '../types';
import { formatTokens, relativeTime, shortSessionId } from '../utils';
import SessionDrawer from '../components/SessionDrawer';

export default function SessionsPage() {
  const { id: routeSessionId } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [data, setData] = useState<PaginatedResponse<SessionSummary> | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [selectedSession, setSelectedSession] = useState<string | null>(routeSessionId || null);

  const pageSize = 20;

  const fetchSessions = useCallback(() => {
    setLoading(true);
    getSessions({
      page,
      page_size: pageSize,
      keyword: keyword || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [page, keyword, dateFrom, dateTo]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  useEffect(() => {
    setSelectedSession(routeSessionId || null);
  }, [routeSessionId]);

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  const openSession = (id: string) => {
    setSelectedSession(id);
    navigate(`/sessions/${id}`, { replace: true });
  };

  const closeDrawer = () => {
    setSelectedSession(null);
    navigate('/sessions', { replace: true });
  };

  return (
    <div>
      <h1 className="mb-4 text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
        Sessions
      </h1>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <div className="relative flex-1" style={{ minWidth: 200 }}>
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2"
            width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            type="text"
            placeholder="Search messages..."
            value={keyword}
            onChange={(e) => {
              setKeyword(e.target.value);
              setPage(1);
            }}
            className="w-full rounded-md border py-2 pl-9 pr-3 text-sm"
            style={{
              backgroundColor: 'var(--bg-surface)',
              borderColor: 'var(--border)',
              color: 'var(--text-primary)',
            }}
          />
        </div>
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => {
            setDateFrom(e.target.value);
            setPage(1);
          }}
          className="rounded-md border px-3 py-2 text-sm"
          style={{
            backgroundColor: 'var(--bg-surface)',
            borderColor: 'var(--border)',
            color: 'var(--text-primary)',
            colorScheme: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light',
          }}
        />
        <input
          type="date"
          value={dateTo}
          onChange={(e) => {
            setDateTo(e.target.value);
            setPage(1);
          }}
          className="rounded-md border px-3 py-2 text-sm"
          style={{
            backgroundColor: 'var(--bg-surface)',
            borderColor: 'var(--border)',
            color: 'var(--text-primary)',
            colorScheme: document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light',
          }}
        />
      </div>

      {/* Table */}
      <div
        className="overflow-hidden rounded-lg border"
        style={{ borderColor: 'var(--border)' }}
      >
        <table className="w-full text-sm">
          <thead>
            <tr style={{ backgroundColor: 'var(--bg-elevated)' }}>
              <Th>Session</Th>
              <Th>First Query</Th>
              <Th align="right">Time</Th>
              <Th align="right">Tokens</Th>
              <Th align="right">Status</Th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i}>
                  {Array.from({ length: 5 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="skeleton h-4 w-full" />
                    </td>
                  ))}
                </tr>
              ))
            ) : data && data.items.length > 0 ? (
              data.items.map((s) => (
                <tr
                  key={s.session_id}
                  className="cursor-pointer border-t transition-colors"
                  style={{ borderColor: 'var(--border-light)' }}
                  onClick={() => openSession(s.session_id)}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <td className="px-4 py-3">
                    <span className="font-mono text-xs" style={{ color: 'var(--accent)' }}>
                      {shortSessionId(s.session_id)}
                    </span>
                  </td>
                  <td className="max-w-xs truncate px-4 py-3" style={{ color: 'var(--text-primary)' }}>
                    {s.first_query || '-'}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right text-xs" style={{ color: 'var(--text-muted)' }}>
                    {relativeTime(s.created_at)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-right font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>
                    {formatTokens(s.total_tokens)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <StatusBadge status={s.status} />
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
                  No sessions found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-center gap-2">
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="rounded-md px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-30"
            style={{ color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
          >
            Prev
          </button>
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            {page} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="rounded-md px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-30"
            style={{ color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
          >
            Next
          </button>
        </div>
      )}

      {/* Drawer */}
      <SessionDrawer sessionId={selectedSession} onClose={closeDrawer} />
    </div>
  );
}

function Th({ children, align = 'left' }: { children: React.ReactNode; align?: 'left' | 'right' }) {
  return (
    <th
      className={`px-4 py-3 text-xs font-medium uppercase tracking-wider ${align === 'right' ? 'text-right' : 'text-left'}`}
      style={{ color: 'var(--text-muted)' }}
    >
      {children}
    </th>
  );
}

function StatusBadge({ status }: { status: string }) {
  const isError = status.toLowerCase().includes('error');
  return (
    <span
      className="inline-block rounded px-1.5 py-0.5 text-[10px] font-medium"
      style={{
        backgroundColor: isError ? 'rgba(239,68,68,0.15)' : 'rgba(34,197,94,0.15)',
        color: isError ? 'var(--danger)' : 'var(--success)',
      }}
    >
      {status}
    </span>
  );
}
