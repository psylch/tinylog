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
      {/* Overlay */}
      <div
        className="fixed inset-0 z-50 bg-black/50 transition-opacity"
        onClick={onClose}
      />
      {/* Drawer */}
      <div
        className="fixed right-0 top-0 z-50 flex h-full w-full flex-col border-l sm:w-3/5"
        style={{
          backgroundColor: 'var(--bg-base)',
          borderColor: 'var(--border)',
        }}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between border-b px-5 py-4"
          style={{ borderColor: 'var(--border)' }}
        >
          <div className="min-w-0 flex-1">
            {loading ? (
              <div className="skeleton h-5 w-48" />
            ) : session ? (
              <>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-medium" style={{ color: 'var(--accent)' }}>
                    {session.session_id.slice(0, 12)}...
                  </span>
                  {session.model && (
                    <span
                      className="rounded px-1.5 py-0.5 text-xs"
                      style={{ backgroundColor: 'var(--bg-elevated)', color: 'var(--text-muted)' }}
                    >
                      {session.model}
                    </span>
                  )}
                </div>
                <div className="mt-1 flex gap-4 text-xs" style={{ color: 'var(--text-muted)' }}>
                  <span>{formatTokens(session.metrics.total_tokens)} tokens</span>
                  {session.metrics.duration != null && (
                    <span>{formatDuration(session.metrics.duration)}</span>
                  )}
                  <span>{relativeTime(session.created_at)}</span>
                </div>
              </>
            ) : (
              <span style={{ color: 'var(--text-muted)' }}>Session not found</span>
            )}
          </div>
          <button
            onClick={onClose}
            className="ml-4 rounded-md p-1.5 transition-colors"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-hover)')}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          {loading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="skeleton h-16 w-full" />
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
  // Group tool messages with their preceding assistant message's tool_calls
  const toolResultMap = new Map<string, Message>();
  for (const msg of messages) {
    if (msg.role === 'tool' && msg.tool_call_id) {
      toolResultMap.set(msg.tool_call_id, msg);
    }
  }

  return (
    <div className="space-y-4">
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
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] ${isUser ? '' : 'w-full'}`}>
        <div
          className="rounded-lg px-4 py-3 text-sm leading-relaxed"
          style={{
            backgroundColor: isUser ? 'var(--accent-muted)' : 'var(--bg-surface)',
            color: 'var(--text-primary)',
            border: isUser ? 'none' : '1px solid var(--border)',
          }}
        >
          <div className="whitespace-pre-wrap break-words">{message.content}</div>
          {/* Inline images */}
          {message.images && message.images.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {message.images.map((fileId) => {
                const file = files.find((f) => f.id === fileId);
                return file ? (
                  <img
                    key={fileId}
                    src={file.url}
                    alt={file.filename}
                    className="max-h-40 rounded border cursor-pointer"
                    style={{ borderColor: 'var(--border)' }}
                    onClick={() => window.open(file.url, '_blank')}
                  />
                ) : null;
              })}
            </div>
          )}
        </div>
        {/* Tool calls below assistant bubble */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="mt-2 space-y-2">
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
    <div
      className="rounded-md border text-xs"
      style={{ borderColor: 'var(--border)', backgroundColor: 'var(--bg-elevated)' }}
    >
      <button
        className="flex w-full items-center gap-2 px-3 py-2 text-left transition-colors"
        style={{ color: 'var(--text-secondary)' }}
        onClick={() => setExpanded(!expanded)}
        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-hover)')}
        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
        </svg>
        <span className="font-mono font-medium" style={{ color: 'var(--accent)' }}>
          {toolCall.name}
        </span>
        <span
          className="ml-auto rounded px-1.5 py-0.5 text-[10px] font-medium"
          style={{
            backgroundColor: isError ? 'rgba(239,68,68,0.15)' : 'rgba(34,197,94,0.15)',
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
            transition: 'transform 0.15s',
          }}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      {expanded && (
        <div className="border-t px-3 py-2" style={{ borderColor: 'var(--border)' }}>
          <div className="mb-2">
            <span className="font-medium" style={{ color: 'var(--text-muted)' }}>Args</span>
            <pre
              className="font-mono mt-1 overflow-x-auto rounded p-2 text-[11px] leading-relaxed"
              style={{ backgroundColor: 'var(--bg-base)', color: 'var(--text-secondary)' }}
            >
              {JSON.stringify(toolCall.args, null, 2)}
            </pre>
          </div>
          {resultContent && (
            <div>
              <span className="font-medium" style={{ color: 'var(--text-muted)' }}>Result</span>
              <pre
                className="font-mono mt-1 max-h-48 overflow-auto rounded p-2 text-[11px] leading-relaxed"
                style={{ backgroundColor: 'var(--bg-base)', color: 'var(--text-secondary)' }}
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
