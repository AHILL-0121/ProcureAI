'use client';

import { useSyncExternalStore } from 'react';
import { API } from './api';

/**
 * The backend runs on a free host that sleeps when idle and takes 30–60 s to boot.
 * `wakeServer()` pings it (no auth, no LLM) until it answers; the landing and sign-in pages call it on load
 * so the server is warming while the visitor reads. Components read the state with `useServerWake()`.
 */
export type WakeState = 'idle' | 'checking' | 'waking' | 'ready' | 'down';

const SLOW_MS = 2500;          // only call it "waking" if the first answer takes longer than this
const RETRY_MS = 3000;
const PING_TIMEOUT_MS = 20000;
const GIVE_UP_MS = 120000;
const AWAKE_KEY = 'procureai.awakeAt';
const AWAKE_FOR_MS = 10 * 60 * 1000;   // the host sleeps after ~15 min idle

let state: WakeState = 'idle';
let startedAt = 0;
let pending: Promise<boolean> | null = null;
const listeners = new Set<() => void>();

function set(next: WakeState) {
  if (state === next) return;
  state = next;
  listeners.forEach((fn) => fn());
}

function recentlyAwake(): boolean {
  try {
    return Date.now() - Number(sessionStorage.getItem(AWAKE_KEY) || 0) < AWAKE_FOR_MS;
  } catch {
    return false;
  }
}

/** Any real API answer proves the server is up. */
export function markAwake() {
  try {
    sessionStorage.setItem(AWAKE_KEY, String(Date.now()));
  } catch {
    /* storage unavailable: state still lives in memory */
  }
  set('ready');
}

async function ping(): Promise<boolean> {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), PING_TIMEOUT_MS);
  try {
    const res = await fetch(`${API}/ping`, { signal: ctl.signal, cache: 'no-store' });
    return res.ok;
  } catch {
    return false;
  } finally {
    clearTimeout(t);
  }
}

/** Resolves true once the server answers, false if it never does within two minutes. Safe to call often. */
export function wakeServer(): Promise<boolean> {
  if (typeof window === 'undefined') return Promise.resolve(false);
  if (state === 'ready') return Promise.resolve(true);
  if (pending) return pending;
  // A visit a few minutes ago means it is probably still up: check quietly, without the slip
  const quiet = recentlyAwake();
  startedAt = Date.now();
  set('checking');
  const slow = quiet ? 0 : window.setTimeout(() => { if (state === 'checking') set('waking'); }, SLOW_MS);
  pending = (async () => {
    while (Date.now() - startedAt < GIVE_UP_MS) {
      if (await ping()) {
        markAwake();
        return true;
      }
      set('waking');
      await new Promise((r) => setTimeout(r, RETRY_MS));
    }
    set('down');
    return false;
  })().finally(() => {
    clearTimeout(slow);
    pending = null;
  });
  return pending;
}

export function wakeStartedAt(): number {
  return startedAt;
}

function subscribe(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function useServerWake(): WakeState {
  return useSyncExternalStore(subscribe, () => state, () => 'idle');
}
