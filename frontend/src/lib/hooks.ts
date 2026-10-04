'use client';

import { useCallback, useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { get, upload } from './api';
import { useRealtime } from './realtime';
import { useToast } from './toast';
import type { Health, UploadItem } from './types';

export function useHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: () => get<Health>('/health'),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function useReviewCount(enabled = true) {
  return useQuery({
    queryKey: ['invoices', 'count', 'review'],
    queryFn: () => get<{ total: number }>('/invoices?queue=review&page_size=1'),
    select: (d) => d.total,
    enabled,
    refetchInterval: 60_000,
  });
}

export const ACCEPT = '.pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg';
const OK_TYPES = ['application/pdf', 'image/png', 'image/jpeg'];
const MAX_BYTES = 15 * 1024 * 1024;

export function useUpload() {
  const { track } = useRealtime();
  const { toast } = useToast();
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);

  const send = useCallback(async (files: File[]) => {
    const valid = files.filter((f) => OK_TYPES.includes(f.type) && f.size <= MAX_BYTES);
    const skipped = files.length - valid.length;
    if (skipped) toast(`${skipped} file${skipped > 1 ? 's' : ''} skipped: only PDF, PNG or JPEG up to 15 MB`, { tone: 'error' });
    if (!valid.length) return;
    setBusy(true);
    try {
      const res = await upload<{ accepted: number; items: UploadItem[] }>(valid);
      track(res.items);
      const dup = res.items.filter((i) => i.duplicate).length;
      const rejected = res.items.filter((i) => !i.invoice_id);
      if (res.accepted) toast(`${res.accepted} invoice${res.accepted > 1 ? 's' : ''} in the tray`);
      if (dup) toast(`${dup} already received earlier; not processed again`);
      rejected.forEach((r) => toast(`${r.filename}: ${r.error}`, { tone: 'error' }));
      qc.invalidateQueries({ queryKey: ['invoices'] });
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Upload failed', { tone: 'error' });
    } finally {
      setBusy(false);
    }
  }, [qc, toast, track]);

  return { send, busy };
}

export function useDebounced<T>(value: T, ms = 250): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setV(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return v;
}

/** Global single-key shortcuts; ignored while typing in a field or when a dialog is open. */
export function useHotkeys(map: Record<string, (e: KeyboardEvent) => void>, deps: unknown[] = []) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (t && (t.closest('input, textarea, select, [contenteditable="true"]') || t.closest('[role="dialog"]'))) return;
      const fn = map[e.key];
      if (fn) fn(e);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
