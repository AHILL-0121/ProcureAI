import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const API_BASE = '/api';

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'API Error');
  }
  return res.json();
}

export async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Upload Error');
  }
  return res.json();
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
}

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-';
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric'
    });
  } catch {
    return dateStr;
  }
}

export function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    RECEIVED: 'bg-sky-100/80 text-sky-800',
    EXTRACTING: 'bg-amber-100/80 text-amber-800',
    EXTRACTED: 'bg-cyan-100/80 text-cyan-800',
    VALIDATING: 'bg-teal-100/80 text-teal-800',
    VALIDATED: 'bg-emerald-100/80 text-emerald-800',
    MATCHING: 'bg-orange-100/80 text-orange-800',
    MATCHED: 'bg-green-100/80 text-green-800',
    DISCREPANCY: 'bg-red-100/80 text-red-800',
    FAILED: 'bg-red-200/80 text-red-900',
  };
  return map[status] || 'bg-surface-100 text-surface-800';
}

export function getMatchColor(result: string): string {
  const map: Record<string, string> = {
    FULL_MATCH: 'bg-emerald-100/80 text-emerald-800 border-emerald-300/60',
    PARTIAL_MATCH: 'bg-amber-100/80 text-amber-800 border-amber-300/60',
    NO_MATCH: 'bg-red-100/80 text-red-800 border-red-300/60',
    PENDING: 'bg-surface-100/80 text-surface-600 border-surface-300/60',
  };
  return map[result] || 'bg-surface-100 text-surface-800';
}
