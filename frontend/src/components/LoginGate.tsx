import { useState } from 'react';
import { setAdminKey } from '../services/api';

export default function LoginGate({ onLogin }: { onLogin: () => void }) {
  const [key, setKey] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!key.trim()) return;

    setLoading(true);
    setError('');

    setAdminKey(key.trim());

    try {
      const res = await fetch('/api/sessions?page=1&page_size=1', {
        headers: { 'X-Admin-Key': key.trim() },
      });
      if (res.status === 401) {
        setError('Invalid admin key');
        localStorage.removeItem('tinylog_admin_key');
      } else {
        onLogin();
      }
    } catch {
      setError('Failed to connect to server');
      localStorage.removeItem('tinylog_admin_key');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4"
      style={{ backgroundColor: 'var(--bg-base)' }}
    >
      <div
        className="w-full max-w-sm rounded-lg border p-6"
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderColor: 'var(--border)',
        }}
      >
        <div className="mb-6 text-center">
          <h1 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>
            TinyLog
          </h1>
          <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>
            Enter your admin key to continue
          </p>
        </div>
        <form onSubmit={handleSubmit}>
          <input
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="Admin key"
            autoFocus
            className="mb-3 w-full rounded-md border px-3 py-2 text-sm"
            style={{
              backgroundColor: 'var(--bg-elevated)',
              borderColor: 'var(--border)',
              color: 'var(--text-primary)',
            }}
          />
          {error && (
            <p className="mb-3 text-xs" style={{ color: 'var(--danger)' }}>
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={loading || !key.trim()}
            className="w-full rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50"
            style={{
              backgroundColor: 'var(--accent)',
              color: '#000',
            }}
            onMouseEnter={(e) => {
              if (!loading) e.currentTarget.style.backgroundColor = 'var(--accent-hover)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--accent)';
            }}
          >
            {loading ? 'Verifying...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
