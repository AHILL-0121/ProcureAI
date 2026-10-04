import { markAwake, wakeServer } from './wake';

export const API = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api').replace(/\/$/, '');

export function wsUrl(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL;
  const u = new URL(API);
  u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
  u.pathname = '/ws';
  return u.toString();
}

const TOKEN_KEY = 'procureai.token';
let token: string | null = null;
let onUnauthorized: (() => void) | null = null;

export function getToken(): string | null {
  if (token) return token;
  try {
    token = localStorage.getItem(TOKEN_KEY);
  } catch {
    token = null;
  }
  return token;
}

export function setToken(value: string | null) {
  token = value;
  try {
    if (value) localStorage.setItem(TOKEN_KEY, value);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable: keep the token in memory only */
  }
}

export function setUnauthorizedHandler(fn: (() => void) | null) {
  onUnauthorized = fn;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function describe(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  return fallback;
}

export async function api<T>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const t = getToken();
  if (t) headers.set('Authorization', `Bearer ${t}`);
  let body = init.body;
  if (init.json !== undefined) {
    headers.set('Content-Type', 'application/json');
    body = JSON.stringify(init.json);
  }
  void wakeServer();   // no-op once the server has answered; otherwise shows the "waking up" slip if it is slow
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, { ...init, headers, body });
  } catch {
    throw new ApiError(0, 'Cannot reach the ProcureAI server. Check your connection and try again.');
  }
  if (res.status < 500) markAwake();
  if (res.status === 401 && path !== '/auth/login') {
    onUnauthorized?.();
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError(res.status, describe(data.detail, res.statusText || 'Request failed'));
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const get = <T,>(path: string) => api<T>(path);
export const post = <T,>(path: string, json?: unknown) => api<T>(path, { method: 'POST', json: json ?? {} });
export const patch = <T,>(path: string, json: unknown) => api<T>(path, { method: 'PATCH', json });
export const put = <T,>(path: string, json: unknown) => api<T>(path, { method: 'PUT', json });
export const del = <T,>(path: string) => api<T>(path, { method: 'DELETE' });

export function upload<T>(files: File[]): Promise<T> {
  const form = new FormData();
  files.forEach((f) => form.append('files', f, f.name));
  return api<T>('/invoices/upload', { method: 'POST', body: form });
}

export function qs(params: Record<string, string | number | undefined | null>): string {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') p.set(k, String(v));
  });
  const s = p.toString();
  return s ? `?${s}` : '';
}
