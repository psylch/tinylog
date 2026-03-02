import { useEffect, useState } from 'react';
import { getFiles, getFileUrl } from '../services/api';
import type { FileInfo, PaginatedResponse } from '../types';

export default function FilesPage() {
  const [data, setData] = useState<PaginatedResponse<FileInfo> | null>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);

  const pageSize = 24;

  useEffect(() => {
    setLoading(true);
    getFiles({ page, page_size: pageSize })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [page]);

  const totalPages = data ? Math.ceil(data.total / pageSize) : 0;

  return (
    <div>
      <h1 className="mb-4 text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
        Files
      </h1>

      {loading ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="skeleton aspect-square rounded-lg" />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
          {data.items.map((file) => (
            <FileCard key={file.id} file={file} onClick={() => setLightboxUrl(getFileUrl(file.id))} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-20">
          <svg
            width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"
            className="mb-3 opacity-50"
          >
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            No files yet
          </p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-center gap-2">
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

      {/* Lightbox */}
      {lightboxUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-8"
          onClick={() => setLightboxUrl(null)}
        >
          <img
            src={lightboxUrl}
            alt="Full size"
            className="max-h-full max-w-full rounded-lg object-contain"
            onClick={(e) => e.stopPropagation()}
          />
          <button
            className="absolute right-6 top-6 rounded-full p-2 text-white/70 transition-colors hover:text-white"
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
      className="group cursor-pointer overflow-hidden rounded-lg border transition-colors"
      style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-surface)' }}
      onClick={onClick}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--accent)')}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
    >
      <div className="aspect-square overflow-hidden" style={{ backgroundColor: 'var(--bg-elevated)' }}>
        {isImage ? (
          <img
            src={getFileUrl(file.id)}
            alt={file.filename}
            className="h-full w-full object-cover transition-transform group-hover:scale-105"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full items-center justify-center">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
            </svg>
          </div>
        )}
      </div>
      <div className="px-2 py-2">
        <p className="truncate text-xs" style={{ color: 'var(--text-secondary)' }}>
          {file.filename}
        </p>
        {file.created_at && (
          <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
            {new Date(file.created_at * 1000).toLocaleDateString()}
          </p>
        )}
      </div>
    </div>
  );
}
