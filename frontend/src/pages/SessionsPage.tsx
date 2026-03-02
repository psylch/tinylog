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
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [keyword, setKeyword] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [selectedSession, setSelectedSession] = useState<string | null>(routeSessionId || null);

  const pageSize = 20;

  const fetchSessions = useCallback(() => {
    setLoading(true);
    setError(null);
    getSessions({
      page,
      page_size: pageSize,
      keyword: keyword || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
      .then(setData)
      .catch((err) => {
        setData(null);
        setError(err instanceof Error ? err.message : 'Failed to load sessions');
      })
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
      <h1 className="text-xl font-semibold text-primary" style={{ marginBottom: '1.25rem' }}>
        Sessions
      </h1>

      {/* Error */}
      {error && (
        <div className="notice" style={{ marginBottom: '1.25rem' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span className="flex-1">{error}</span>
          <button
            onClick={() => { setError(null); fetchSessions(); }}
            style={{ fontSize: '0.75rem', fontWeight: 500, textDecoration: 'underline', color: 'inherit', background: 'none', border: 'none', cursor: 'pointer', opacity: 0.8 }}
            onMouseEnter={e => e.currentTarget.style.opacity = '1'}
            onMouseLeave={e => e.currentTarget.style.opacity = '0.8'}
          >
            Retry
          </button>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 flex-wrap" style={{ marginBottom: '1.25rem' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '200px' }}>
          <svg
            style={{ position: 'absolute', left: '0.75rem', top: '50%', transform: 'translateY(-50%)' }}
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
            className="input-field"
            style={{ paddingLeft: '2.25rem', boxShadow: 'none' }}
          />
        </div>
        <input
          type="date"
          value={dateFrom}
          onChange={(e) => {
            setDateFrom(e.target.value);
            setPage(1);
          }}
          className="input-field"
          style={{ width: 'auto', boxShadow: 'none' }}
        />
        <input
          type="date"
          value={dateTo}
          onChange={(e) => {
            setDateTo(e.target.value);
            setPage(1);
          }}
          className="input-field"
          style={{ width: 'auto', boxShadow: 'none' }}
        />
      </div>

      {/* Table */}
      <div className="table-container">
        <table className="premium-table">
          <thead>
            <tr>
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
                    <td key={j}>
                      <div className="skeleton" style={{ height: '1rem', width: '100%', borderRadius: '4px' }} />
                    </td>
                  ))}
                </tr>
              ))
            ) : data && data.items.length > 0 ? (
              data.items.map((s) => (
                <tr
                  key={s.session_id}
                  style={{ cursor: 'pointer' }}
                  onClick={() => openSession(s.session_id)}
                >
                  <td>
                    <span className="font-mono text-xs font-medium" style={{ color: 'var(--accent)' }}>
                      {shortSessionId(s.session_id)}
                    </span>
                  </td>
                  <td style={{ maxWidth: '20rem' }} className="truncate text-primary">
                    {s.first_query || '-'}
                  </td>
                  <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }} className="text-xs text-muted">
                    {relativeTime(s.created_at)}
                  </td>
                  <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }} className="font-mono text-xs text-secondary">
                    {formatTokens(s.total_tokens)}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <StatusBadge status={s.status} />
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} style={{ padding: '4rem 1rem', textAlign: 'center' }}>
                  <div className="flex flex-col items-center justify-center gap-3">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ opacity: 0.3 }}>
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                    </svg>
                    <p className="text-sm text-muted">No sessions found</p>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3" style={{ marginTop: '1.25rem' }}>
          <button
            disabled={page <= 1}
            onClick={() => setPage((p) => p - 1)}
            className="btn btn-secondary text-xs"
          >
            Prev
          </button>
          <span className="font-mono text-xs text-muted">
            {page} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="btn btn-secondary text-xs"
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
    <th style={{ textAlign: align }}>
      {children}
    </th>
  );
}

function StatusBadge({ status }: { status: string }) {
  const lower = status.toLowerCase();
  const isError = lower.includes('error') || lower.includes('fail');
  const isPaused = lower.includes('pause') || lower.includes('pending');

  let bgColor: string;
  let textColor: string;

  if (isError) {
    bgColor = 'var(--danger-muted)';
    textColor = 'var(--danger)';
  } else if (isPaused) {
    bgColor = 'var(--warning-muted)';
    textColor = 'var(--warning)';
  } else {
    bgColor = 'var(--success-muted)';
    textColor = 'var(--success)';
  }

  return (
    <span
      className="badge"
      style={{ backgroundColor: bgColor, color: textColor }}
    >
      {status}
    </span>
  );
}
