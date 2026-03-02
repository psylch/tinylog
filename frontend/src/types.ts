export interface SessionSummary {
  session_id: string;
  created_at: number;
  updated_at: number | null;
  first_query: string;
  message_count: number;
  model: string | null;
  status: string;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  duration: number | null;
  ttft: number | null;
  tool_names: string[];
  has_images: boolean;
}

export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result: string;
}

export interface TokenMetrics {
  input_tokens: number;
  output_tokens: number;
  time_to_first_token?: number;
}

export interface Message {
  index: number;
  role: 'user' | 'assistant' | 'tool';
  content: string;
  created_at: number | null;
  reasoning?: string | null;
  token_metrics?: TokenMetrics | null;
  tool_calls?: ToolCall[] | null;
  tool_name?: string | null;
  tool_call_id?: string | null;
  images?: string[];
}

export interface FileInfo {
  id: string;
  filename: string;
  mime_type: string;
  size: number;
  url: string;
  session_id?: string;
  created_at?: number;
}

export interface SessionDetail {
  session_id: string;
  created_at: number;
  model: string | null;
  metrics: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    cache_read_tokens?: number;
    reasoning_tokens?: number;
    duration?: number;
  };
  messages: Message[];
  tools: Record<string, unknown>[];
  files: FileInfo[];
}

export interface DailyMetrics {
  date: string;
  sessions: number;
  messages: number;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  avg_duration: number | null;
  avg_ttft: number | null;
}

export interface OverviewStats {
  period: string;
  current: {
    sessions: number;
    messages: number;
    total_tokens: number;
    input_tokens: number;
    output_tokens: number;
    cache_hit_rate: number;
    avg_duration: number;
    avg_ttft: number;
  };
  previous: {
    sessions: number;
    messages: number;
    total_tokens: number;
  };
  trends: {
    sessions: number;
    messages: number;
    total_tokens: number;
    avg_ttft: number;
  };
  tool_calls: {
    total: number;
    by_tool: Record<string, number>;
  };
}

export interface PaginatedResponse<T> {
  total: number;
  page: number;
  page_size: number;
  items: T[];
}

export interface AppConfig {
  needs_auth: boolean;
  theme: string;
  title: string;
}
