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
    <div className="app-container flex justify-center items-center" style={{ padding: '0 1rem' }}>
      <div className="card" style={{ width: '100%', maxWidth: '24rem', padding: '2rem' }}>
        <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
          <h1 className="text-xl font-semibold text-primary">TinyLog</h1>
          <p className="text-sm text-muted" style={{ marginTop: '0.25rem' }}>
            Enter your admin key to continue
          </p>
        </div>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="Admin key"
            autoFocus
            className="input-field"
          />
          {error && (
            <p className="text-xs" style={{ color: 'var(--danger)' }}>
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={loading || !key.trim()}
            className="btn btn-primary"
            style={{ width: '100%', marginTop: '0.5rem', padding: '0.75rem' }}
          >
            {loading ? 'Verifying...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
