import { useEffect, useState } from 'react';
import { getFiles, getFileUrl } from '../services/api';
import type { FileInfo, PaginatedResponse } from '../types';

export default function FilesPage() {
  const [data, setData] = useState<PaginatedResponse<FileInfo> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);

  const pageSize = 24;

  useEffect(() => {
    setLoading(true);
    setError(null);
    getFiles({ page, page_size: pageSize })
      .then(setData)
      .catch((err) => {
        setData(null);
        setError(err instanceof Error ? err.message : 'Failed to load files');
      })
      .finally(() => setLoading(false));
  }, [page]);

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <div>
      <h1 className="text-xl font-semibold text-primary" style={{ marginBottom: '1.25rem' }}>
        Files
      </h1>

      {error && (
        <div className="notice" style={{ marginBottom: '1.25rem' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span className="flex-1">{error}</span>
        </div>
      )}

      {loading ? (
        <div className="grid-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '1rem' }}>
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="skeleton" style={{ aspectRatio: '1/1', borderRadius: '12px' }} />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <div className="grid-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '1rem' }}>
          {data.items.map((file) => (
            <FileCard key={file.id} file={file} onClick={() => setLightboxUrl(getFileUrl(file.id))} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center" style={{ padding: '5rem 0' }}>
          <svg
            width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
            style={{ marginBottom: '0.75rem', opacity: 0.3 }}
          >
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
          <p className="text-sm text-muted">
            No files yet
          </p>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3" style={{ marginTop: '1.5rem' }}>
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

      {lightboxUrl && (
        <div
          className="lightbox-overlay"
          onClick={() => setLightboxUrl(null)}
        >
          <img
            src={lightboxUrl}
            alt="Full size"
            style={{ maxHeight: '100%', maxWidth: '100%', borderRadius: '12px', objectFit: 'contain', boxShadow: '0 24px 48px rgba(0,0,0,0.5)' }}
            onClick={(e) => e.stopPropagation()}
          />
          <button
            style={{ position: 'absolute', right: '1.5rem', top: '1.5rem', padding: '0.5rem', borderRadius: '50%', color: 'rgba(255,255,255,0.7)', transition: 'color 0.2s', background: 'none', border: 'none', cursor: 'pointer' }}
            onMouseEnter={e => e.currentTarget.style.color = '#fff'}
            onMouseLeave={e => e.currentTarget.style.color = 'rgba(255,255,255,0.7)'}
            onClick={() => setLightboxUrl(null)}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}

function FileCard({ file, onClick }: { file: FileInfo; onClick: () => void }) {
  const isImage = file.mime_type.startsWith('image/');

  return (
    <div
      className="card"
      onClick={onClick}
      style={{ cursor: 'pointer', overflow: 'hidden' }}
      onMouseEnter={e => {
        const img = e.currentTarget.querySelector('img');
        if (img) img.style.transform = 'scale(1.05)';
      }}
      onMouseLeave={e => {
        const img = e.currentTarget.querySelector('img');
        if (img) img.style.transform = 'scale(1)';
      }}
    >
      <div style={{ aspectRatio: '1/1', overflow: 'hidden', backgroundColor: 'var(--bg-elevated)' }}>
        {isImage ? (
          <img
            src={getFileUrl(file.id)}
            alt={file.filename}
            style={{ height: '100%', width: '100%', objectFit: 'cover', transition: 'transform 0.3s ease' }}
            loading="lazy"
          />
        ) : (
          <div className="flex items-center justify-center" style={{ height: '100%' }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>
        )}
      </div>
      <div style={{ padding: '0.75rem' }}>
        <p className="truncate text-xs font-medium text-secondary">
          {file.filename}
        </p>
        {file.created_at && (
          <p className="text-muted" style={{ marginTop: '0.125rem', fontSize: '0.625rem' }}>
            {new Date(file.created_at * 1000).toLocaleDateString()}
          </p>
        )}
      </div>
    </div>
  );
}
