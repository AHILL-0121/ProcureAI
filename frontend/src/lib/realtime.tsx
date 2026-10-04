'use client';

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { getToken, wsUrl } from './api';
import type { MatchResult, UploadItem, WSEvent } from './types';

export interface TrayItem {
  id: string;
  file: string;
  step: number;             // 0..4 current station, 5 = finished
  status?: string;
  result?: MatchResult;
  error?: string;
  startedAt: number;
  finishedAt?: number;
  seen?: boolean;           // a worker has picked it up (false = still waiting in the queue)
}

interface Realtime {
  connected: boolean;
  tray: TrayItem[];
  track: (items: UploadItem[]) => void;
  dismiss: (id: string) => void;
  clear: () => void;
  subscribe: (fn: (e: WSEvent) => void) => () => void;
}

const RealtimeContext = createContext<Realtime>({
  connected: false,
  tray: [],
  track: () => {},
  dismiss: () => {},
  clear: () => {},
  subscribe: () => () => {},
});

export function useRealtime() {
  return useContext(RealtimeContext);
}

const STEP_INDEX: Record<string, number> = { received: 0, read: 1, check: 2, lookup: 3, match: 4 };

export function RealtimeProvider({ children, enabled }: { children: ReactNode; enabled: boolean }) {
  const qc = useQueryClient();
  const [connected, setConnected] = useState(false);
  const [tray, setTray] = useState<TrayItem[]>([]);
  const listeners = useRef(new Set<(e: WSEvent) => void>());

  const subscribe = useCallback((fn: (e: WSEvent) => void) => {
    listeners.current.add(fn);
    return () => {
      listeners.current.delete(fn);
    };
  }, []);

  const track = useCallback((items: UploadItem[]) => {
    const now = Date.now();
    setTray((t) => {
      const next = [...t];
      for (const it of items) {
        if (!it.invoice_id || it.duplicate || next.some((x) => x.id === it.invoice_id)) continue;
        next.push({ id: it.invoice_id, file: it.filename, step: 0, startedAt: now });
      }
      return next;
    });
  }, []);

  const dismiss = useCallback((id: string) => setTray((t) => t.filter((x) => x.id !== id)), []);
  const clear = useCallback(() => setTray([]), []);

  const onEvent = useCallback((e: WSEvent) => {
    listeners.current.forEach((fn) => fn(e));
    if (e.event === 'status_update' || e.event === 'match_complete' || e.event === 'processing_error') {
      setTray((t) => {
        const exists = t.find((x) => x.id === e.invoice_id);
        const base: TrayItem = exists ?? { id: e.invoice_id!, file: e.file || e.invoice_number || 'Invoice', step: 0, startedAt: Date.now() };
        const updated: TrayItem = { ...base, seen: true };
        if (e.event === 'status_update' && e.step) updated.step = Math.max(updated.step, STEP_INDEX[e.step] ?? 0);
        if (e.event === 'match_complete') {
          updated.step = 5;
          updated.result = e.match_result;
          updated.status = e.status;
          updated.finishedAt = Date.now();
        }
        if (e.event === 'processing_error') {
          updated.error = e.error;
          updated.status = 'FAILED';
          updated.finishedAt = Date.now();
        }
        if (e.file) updated.file = e.file;
        return exists ? t.map((x) => (x.id === updated.id ? updated : x)) : [...t, updated].slice(-20);
      });
    }
    if (e.event === 'match_complete' || e.event === 'processing_error' || e.event === 'review_update') {
      qc.invalidateQueries({ queryKey: ['invoices'] });
      qc.invalidateQueries({ queryKey: ['stats'] });
      if (e.invoice_id) qc.invalidateQueries({ queryKey: ['invoice', e.invoice_id] });
    }
  }, [qc]);

  // finished items leave the tray after a while
  useEffect(() => {
    const t = window.setInterval(() => {
      const now = Date.now();
      setTray((items) => items.filter((x) => !x.finishedAt || now - x.finishedAt < 9000));
    }, 2000);
    return () => window.clearInterval(t);
  }, []);

  useEffect(() => {
    if (!enabled) return;
    let ws: WebSocket | null = null;
    let retry = 0;
    let timer: number | undefined;
    let ping: number | undefined;
    let closed = false;

    const connect = () => {
      const token = getToken();
      if (!token || closed) return;
      ws = new WebSocket(`${wsUrl()}?token=${encodeURIComponent(token)}`);
      ws.onopen = () => {
        retry = 0;
        setConnected(true);
        ping = window.setInterval(() => ws?.readyState === WebSocket.OPEN && ws.send('ping'), 25000);
      };
      ws.onmessage = (m) => {
        try {
          onEvent(JSON.parse(m.data) as WSEvent);
        } catch {
          /* ignore malformed frames */
        }
      };
      ws.onclose = (ev) => {
        setConnected(false);
        window.clearInterval(ping);
        if (closed || ev.code === 4401) return;
        const delay = Math.min(30000, 1000 * 2 ** retry++);
        timer = window.setTimeout(connect, delay);
      };
      ws.onerror = () => ws?.close();
    };
    connect();
    return () => {
      closed = true;
      window.clearTimeout(timer);
      window.clearInterval(ping);
      ws?.close();
    };
  }, [enabled, onEvent]);

  return (
    <RealtimeContext.Provider value={{ connected, tray, track, dismiss, clear, subscribe }}>
      {children}
    </RealtimeContext.Provider>
  );
}
