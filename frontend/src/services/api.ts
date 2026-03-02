import type {
  AppConfig,
  DailyMetrics,
  FileInfo,
  OverviewStats,
  PaginatedResponse,
  SessionDetail,
  SessionSummary,
} from '../types';

const BASE = '/api';

function getAdminKey(): string | null {
  return localStorage.getItem('tinylog_admin_key');
}

export function setAdminKey(key: string) {
  localStorage.setItem('tinylog_admin_key', key);
}

export function clearAdminKey() {
  localStorage.removeItem('tinylog_admin_key');
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string>),
  };

  const key = getAdminKey();
  if (key) {
    headers['X-Admin-Key'] = key;
  }

  const res = await fetch(`${BASE}${path}`, { ...init, headers });

  if (res.status === 401) {
    clearAdminKey();
    window.location.reload();
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

export async function getConfig(): Promise<AppConfig> {
  const res = await fetch(`${BASE}/config`);
  return res.json();
}

export async function checkHealth(): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/health`);
  return res.json();
}

export async function getSessions(params: {
  page?: number;
  page_size?: number;
  keyword?: string;
  date_from?: string;
  date_to?: string;
  sort?: string;
}): Promise<PaginatedResponse<SessionSummary>> {
  const search = new URLSearchParams();
  if (params.page) search.set('page', String(params.page));
  if (params.page_size) search.set('page_size', String(params.page_size));
  if (params.keyword) search.set('keyword', params.keyword);
  if (params.date_from) search.set('date_from', params.date_from);
  if (params.date_to) search.set('date_to', params.date_to);
  if (params.sort) search.set('sort', params.sort);
  const qs = search.toString();
  return request(`/sessions${qs ? '?' + qs : ''}`);
}

export async function getSession(sessionId: string): Promise<SessionDetail> {
  return request(`/sessions/${encodeURIComponent(sessionId)}`);
}

export async function getOverview(period: string): Promise<OverviewStats> {
  return request(`/statistics/overview?period=${encodeURIComponent(period)}`);
}

export async function getDailyMetrics(dateFrom: string, dateTo: string): Promise<{ data: DailyMetrics[] }> {
  return request(`/statistics/daily?date_from=${encodeURIComponent(dateFrom)}&date_to=${encodeURIComponent(dateTo)}`);
}

export async function getToolStats(dateFrom: string, dateTo: string) {
  return request<{ summary: Record<string, number>; daily: Record<string, unknown>[] }>(
    `/statistics/tools?date_from=${encodeURIComponent(dateFrom)}&date_to=${encodeURIComponent(dateTo)}`
  );
}

export async function getFiles(params?: {
  page?: number;
  page_size?: number;
}): Promise<PaginatedResponse<FileInfo>> {
  const search = new URLSearchParams();
  if (params?.page) search.set('page', String(params.page));
  if (params?.page_size) search.set('page_size', String(params.page_size));
  const qs = search.toString();
  return request(`/files${qs ? '?' + qs : ''}`);
}

export function getFileUrl(fileId: string): string {
  return `${BASE}/files/${encodeURIComponent(fileId)}`;
}
