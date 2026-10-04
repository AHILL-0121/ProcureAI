'use client';

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';

export type Fx = 'full' | 'subtle' | 'off';
export type Density = 'comfortable' | 'ledger';
export type SidebarState = 'open' | 'closed';

interface Prefs {
  fx: Fx;
  density: Density;
  sidebar: SidebarState;
  setFx: (v: Fx) => void;
  setDensity: (v: Density) => void;
  toggleSidebar: () => void;
}

const PrefsContext = createContext<Prefs>({
  fx: 'full', density: 'comfortable', sidebar: 'open', setFx: () => {}, setDensity: () => {}, toggleSidebar: () => {},
});

export function usePrefs() {
  return useContext(PrefsContext);
}

function read<T extends string>(key: string, allowed: readonly T[], fallback: T): T {
  try {
    const v = localStorage.getItem(key) as T | null;
    return v && allowed.includes(v) ? v : fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* ignore */
  }
}

export function PrefsProvider({ children }: { children: ReactNode }) {
  const [fx, setFxState] = useState<Fx>('full');
  const [density, setDensityState] = useState<Density>('comfortable');
  const [sidebar, setSidebar] = useState<SidebarState>('open');

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    setFxState(read<Fx>('procureai.fx', ['full', 'subtle', 'off'], reduced ? 'off' : 'full'));
    setDensityState(read<Density>('procureai.density', ['comfortable', 'ledger'], 'comfortable'));
    setSidebar(read<SidebarState>('procureai.sidebar', ['open', 'closed'], 'open'));
  }, []);

  useEffect(() => {
    document.documentElement.dataset.sidebar = sidebar;
  }, [sidebar]);

  useEffect(() => {
    document.documentElement.dataset.fx = fx;
  }, [fx]);

  useEffect(() => {
    document.documentElement.dataset.density = density;
  }, [density]);

  const setFx = useCallback((v: Fx) => {
    setFxState(v);
    write('procureai.fx', v);
  }, []);

  const setDensity = useCallback((v: Density) => {
    setDensityState(v);
    write('procureai.density', v);
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebar((s) => {
      const next = s === 'open' ? 'closed' : 'open';
      write('procureai.sidebar', next);
      return next;
    });
  }, []);

  return (
    <PrefsContext.Provider value={{ fx, density, sidebar, setFx, setDensity, toggleSidebar }}>{children}</PrefsContext.Provider>
  );
}
