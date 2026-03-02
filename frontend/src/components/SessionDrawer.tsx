import { useEffect, useState } from 'react';
import { getSession } from '../services/api';
import type { SessionDetail, Message, ToolCall } from '../types';
import { formatTokens, formatDuration, relativeTime } from '../utils';

interface SessionDrawerProps {
  sessionId: string | null;
  onClose: () => void;
}

export default function SessionDrawer({ sessionId, onClose }: SessionDrawerProps) {
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!sessionId) {
      setSession(null);
      return;
    }
    setLoading(true);
    getSession(sessionId)
      .then(setSession)
      .catch(() => setSession(null))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (!sessionId) return null;

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <div className="drawer-panel">
        <div className="drawer-header">
          <div style={{ flex: 1, minWidth: 0 }}>
            {loading ? (
              <div className="skeleton" style={{ height: '1.25rem', width: '12rem' }} />
            ) : session ? (
              <>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-medium" style={{ color: 'var(--accent)' }}>
                    {session.session_id.slice(0, 12)}...
                  </span>
                  {session.model && (
                    <span className="badge" style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>
                      {session.model}
                    </span>
                  )}
                </div>
                <div style={{ marginTop: '0.25rem', display: 'flex', gap: '1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <span>{formatTokens(session.metrics.total_tokens)} tokens</span>
                  {session.metrics.duration != null && (
                    <span>{formatDuration(session.metrics.duration)}</span>
                  )}
                  <span>{relativeTime(session.created_at)}</span>
                </div>
              </>
            ) : (
              <span className="text-muted">Session not found</span>
            )}
          </div>
          <button
            onClick={onClose}
            className="btn btn-ghost"
            style={{ padding: '0.375rem', borderRadius: '6px', marginLeft: '1rem' }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="drawer-content">
          {loading ? (
            <div className="flex flex-col gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="skeleton" style={{ height: '4rem', width: '100%' }} />
              ))}
            </div>
          ) : session ? (
            <MessageList messages={session.messages} files={session.files} />
          ) : null}
        </div>
      </div>
    </>
  );
}

function MessageList({ messages, files }: { messages: Message[]; files: SessionDetail['files'] }) {
  const toolResultMap = new Map<string, Message>();
  for (const msg of messages) {
    if (msg.role === 'tool' && msg.tool_call_id) {
      toolResultMap.set(msg.tool_call_id, msg);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {messages
        .filter((m) => m.role !== 'tool')
        .map((msg) => (
          <MessageBubble
            key={msg.index}
            message={msg}
            toolResultMap={toolResultMap}
            files={files}
          />
        ))}
    </div>
  );
}

function MessageBubble({
  message,
  toolResultMap,
  files,
}: {
  message: Message;
  toolResultMap: Map<string, Message>;
  files: SessionDetail['files'];
}) {
  const isUser = message.role === 'user';

  return (
    <div className="flex" style={{ justifyContent: isUser ? 'flex-end' : 'flex-start' }}>
      <div style={{ width: isUser ? 'auto' : '100%', maxWidth: '100%' }}>
        <div className={`msg-bubble ${isUser ? 'msg-user' : 'msg-ai'}`}>
          <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
          {message.images && message.images.length > 0 && (
            <div className="flex flex-wrap gap-2" style={{ marginTop: '0.5rem' }}>
              {message.images.map((fileId) => {
                const file = files.find((f) => f.id === fileId);
                return file ? (
                  <img
                    key={fileId}
                    src={file.url}
                    alt={file.filename}
                    style={{ maxHeight: '10rem', borderRadius: '4px', border: '1px solid var(--border)', cursor: 'pointer' }}
                    onClick={() => window.open(file.url, '_blank')}
                  />
                ) : null;
              })}
            </div>
          )}
        </div>
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="flex flex-col gap-2" style={{ marginTop: '0.5rem' }}>
            {message.tool_calls.map((tc) => (
              <ToolCallCard key={tc.id} toolCall={tc} toolResult={toolResultMap.get(tc.id)} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ToolCallCard({ toolCall, toolResult }: { toolCall: ToolCall; toolResult?: Message }) {
  const [expanded, setExpanded] = useState(false);

  const resultContent = toolResult?.content || toolCall.result;
  const isError = resultContent?.includes('"error"') || resultContent?.includes('Error');

  return (
    <div className={`tool-card ${expanded ? 'expanded' : ''}`}>
      <button
        className="tool-card-header text-left"
        style={{ width: '100%', color: 'var(--text-secondary)' }}
        onClick={() => setExpanded(!expanded)}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
        </svg>
        <span className="font-mono font-medium" style={{ color: 'var(--accent)' }}>
          {toolCall.name}
        </span>
        <span
          className="badge"
          style={{
            marginLeft: 'auto',
            backgroundColor: isError ? 'var(--danger-muted)' : 'var(--success-muted)',
            color: isError ? 'var(--danger)' : 'var(--success)',
          }}
        >
          {isError ? 'error' : 'success'}
        </span>
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          style={{
            transform: expanded ? 'rotate(180deg)' : 'rotate(0)',
            transition: 'transform 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
          }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      {expanded && (
        <div className="tool-card-body">
          <div style={{ marginBottom: '0.5rem' }}>
            <span style={{ fontWeight: 500, color: 'var(--text-muted)' }}>Args</span>
            <pre
              className="font-mono"
              style={{ marginTop: '0.25rem', overflowX: 'auto', borderRadius: '4px', padding: '0.5rem', backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border)', fontSize: '0.6875rem', lineHeight: 1.6, color: 'var(--text-secondary)' }}
            >
              {JSON.stringify(toolCall.args, null, 2)}
            </pre>
          </div>
          {resultContent && (
            <div>
              <span style={{ fontWeight: 500, color: 'var(--text-muted)' }}>Result</span>
              <pre
                className="font-mono"
                style={{ marginTop: '0.25rem', maxHeight: '12rem', overflow: 'auto', borderRadius: '4px', padding: '0.5rem', backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border)', fontSize: '0.6875rem', lineHeight: 1.6, color: 'var(--text-secondary)' }}
              >
                {formatJson(resultContent)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function formatJson(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}
