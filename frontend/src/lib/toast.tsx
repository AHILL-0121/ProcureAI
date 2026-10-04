'use client';

import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';

interface Slip {
  id: number;
  message: string;
  tone?: 'default' | 'error';
  action?: { label: string; run: () => void };
}

interface ToastApi {
  toast: (message: string, opts?: { tone?: Slip['tone']; action?: Slip['action']; duration?: number }) => void;
}

const ToastContext = createContext<ToastApi>({ toast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [slips, setSlips] = useState<Slip[]>([]);
  const seq = useRef(0);

  const dismiss = useCallback((id: number) => setSlips((s) => s.filter((x) => x.id !== id)), []);

  const toast = useCallback<ToastApi['toast']>((message, opts = {}) => {
    const id = ++seq.current;
    setSlips((s) => [...s.slice(-2), { id, message, tone: opts.tone, action: opts.action }]);
    window.setTimeout(() => dismiss(id), opts.duration ?? (opts.action ? 6500 : 4000));
  }, [dismiss]);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="slips" role="status" aria-live="polite">
        {slips.map((s) => (
          <div key={s.id} className={`slip ${s.tone === 'error' ? 'slip--error' : ''}`}>
            <span>{s.message}</span>
            {s.action && (
              <button type="button" onClick={() => { s.action!.run(); dismiss(s.id); }}>
                {s.action.label}
              </button>
            )}
            <button type="button" className="slip__close" aria-label="Dismiss" onClick={() => dismiss(s.id)}>×</button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
