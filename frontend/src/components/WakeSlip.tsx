'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { useServerWake, wakeServer, wakeStartedAt } from '@/lib/wake';

/** A paper slip pinned to the corner while the sleeping backend boots. Silent on the landing page. */
export function WakeSlip() {
  const state = useServerWake();
  const path = usePathname();
  const [, tick] = useState(0);
  const show = path !== '/' && (state === 'waking' || state === 'down');

  useEffect(() => {
    if (state !== 'waking') return;
    const id = window.setInterval(() => tick((n) => n + 1), 1000);
    return () => window.clearInterval(id);
  }, [state]);

  if (!show) return null;
  const secs = Math.max(0, Math.round((Date.now() - wakeStartedAt()) / 1000));

  return (
    <div className={`wake-slip ${state === 'down' ? 'wake-slip--down' : ''}`} role="status" aria-live="polite">
      {state === 'waking' ? (
        <>
          <span className="wake-slip__lamp" aria-hidden />
          <div>
            <p className="label">Opening the office · <span className="num">{secs}s</span></p>
            <p>The server sleeps when nobody is using it. It&apos;s waking now and usually takes 30–60 seconds.</p>
          </div>
        </>
      ) : (
        <div>
          <p className="label">Server not answering</p>
          <p>It didn&apos;t wake within two minutes. <button type="button" className="linkish" onClick={() => void wakeServer()}>Try again</button></p>
        </div>
      )}
    </div>
  );
}
