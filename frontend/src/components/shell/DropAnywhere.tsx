'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth';
import { can } from '@/lib/format';
import { useUpload } from '@/lib/hooks';

/** Drop files anywhere on the app: an in-tray slides up while dragging. */
export function DropAnywhere() {
  const { user } = useAuth();
  const { send } = useUpload();
  const [active, setActive] = useState(false);
  const allowed = can.edit(user?.role);

  useEffect(() => {
    if (!allowed) return;
    let depth = 0;
    const hasFiles = (e: DragEvent) => Array.from(e.dataTransfer?.types ?? []).includes('Files');
    // Areas with their own drop handling (e.g. the ERP import in Settings) opt out with data-own-drop
    const ownDrop = (e: DragEvent) => e.target instanceof Element && !!e.target.closest('[data-own-drop]');
    const enter = (e: DragEvent) => {
      if (!hasFiles(e)) return;
      if (ownDrop(e)) {
        setActive(false);
        return;
      }
      depth++;
      setActive(true);
    };
    const leave = () => {
      depth = Math.max(0, depth - 1);
      if (!depth) setActive(false);
    };
    const over = (e: DragEvent) => {
      if (hasFiles(e) && !ownDrop(e)) e.preventDefault();
    };
    const drop = (e: DragEvent) => {
      if (!hasFiles(e) || ownDrop(e)) return;
      e.preventDefault();
      depth = 0;
      setActive(false);
      const files = Array.from(e.dataTransfer?.files ?? []);
      if (files.length) send(files);
    };
    window.addEventListener('dragenter', enter);
    window.addEventListener('dragleave', leave);
    window.addEventListener('dragover', over);
    window.addEventListener('drop', drop);
    return () => {
      window.removeEventListener('dragenter', enter);
      window.removeEventListener('dragleave', leave);
      window.removeEventListener('dragover', over);
      window.removeEventListener('drop', drop);
    };
  }, [allowed, send]);

  if (!allowed) return null;
  return (
    <div className={`dropzone ${active ? 'is-active' : ''}`} aria-hidden={!active}>
      <div className="dropzone__tray">
        <svg viewBox="0 0 160 60" aria-hidden>
          <path d="M6 14h44l7 14h46l7-14h44v40H6z" />
        </svg>
        <b className="display">Drop into the tray</b>
        <span className="label">PDF · PNG · JPEG · up to 15 MB each</span>
      </div>
    </div>
  );
}
