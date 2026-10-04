'use client';

import { useRef } from 'react';
import { MagnifyingGlass, Plus } from '@phosphor-icons/react';
import { Key } from '@/components/ui';
import { useAuth } from '@/lib/auth';
import { can } from '@/lib/format';
import { ACCEPT, useHealth, useUpload } from '@/lib/hooks';
import { usePrefs, type Fx } from '@/lib/prefs';
import { useRealtime } from '@/lib/realtime';

export function HealthPill() {
  const { data, isError } = useHealth();
  const { connected } = useRealtime();
  let tone = 'ok';
  let text = 'All systems';
  if (isError) {
    tone = 'bad';
    text = 'Server unreachable';
  } else if (data) {
    if (data.erp.status !== 'online') {
      tone = 'bad';
      text = 'ERP data missing';
    } else if (data.vision_ocr.groq_status !== 'online') {
      tone = 'hold';
      text = data.vision_ocr.groq_status === 'not_configured' ? 'Reading not configured' : 'Reading degraded';
    } else if (!connected) {
      tone = 'hold';
      text = 'Live updates paused';
    }
  }
  const title = data
    ? `Reading: ${data.vision_ocr.groq_status} (${data.vision_ocr.model}) · ERP: ${data.erp.total_purchase_orders} POs · queue: ${data.queue_depth}`
    : undefined;
  return (
    <span className={`health health--${tone}`} title={title}>
      <i aria-hidden />
      {data || isError ? text : 'Checking…'}
    </span>
  );
}

export function FxSwitch() {
  const { fx, setFx } = usePrefs();
  const opts: { v: Fx; label: string }[] = [
    { v: 'full', label: 'Full' },
    { v: 'subtle', label: 'Subtle' },
    { v: 'off', label: 'Off' },
  ];
  return (
    <div className="seg" role="group" aria-label="Paper effects">
      <span className="seg__label">Effects</span>
      {opts.map((o) => (
        <button key={o.v} type="button" aria-pressed={fx === o.v} onClick={() => setFx(o.v)}>{o.label}</button>
      ))}
    </div>
  );
}

export function TopBar({ onSearch }: { onSearch: () => void }) {
  const { user } = useAuth();
  const input = useRef<HTMLInputElement>(null);
  const { send, busy } = useUpload();
  return (
    <header className="top">
      <button type="button" className="search" onClick={onSearch} aria-label="Search invoices, POs and vendors (Ctrl K)">
        <MagnifyingGlass size={16} aria-hidden />
        <span>Find invoice, PO, vendor…</span>
        <kbd>Ctrl K</kbd>
      </button>
      <HealthPill />
      <FxSwitch />
      {can.edit(user?.role) && (
        <>
          <Key variant="primary" onClick={() => input.current?.click()} busy={busy}>
            <Plus size={16} weight="bold" aria-hidden /> Add invoices
          </Key>
          <input
            ref={input}
            type="file"
            accept={ACCEPT}
            multiple
            hidden
            onChange={(e) => {
              const files = Array.from(e.target.files ?? []);
              e.target.value = '';
              if (files.length) send(files);
            }}
          />
        </>
      )}
    </header>
  );
}
