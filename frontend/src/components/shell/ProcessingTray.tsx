'use client';

import Link from 'next/link';
import { AnimatePresence, motion } from 'motion/react';
import { X } from '@phosphor-icons/react';
import { RESULT } from '@/lib/format';
import { usePrefs } from '@/lib/prefs';
import { useRealtime, type TrayItem } from '@/lib/realtime';

const STATIONS = ['Received', 'Read', 'Check', 'Look up', 'Match'];
const WORKING = ['Receiving…', 'Reading the document…', 'Checking fields and vendor…', 'Looking up PO and receipts…', 'Matching lines…'];

export function PunchRail({ step, failed }: { step: number; failed?: boolean }) {
  return (
    <div className="rail" role="progressbar" aria-valuemin={0} aria-valuemax={5} aria-valuenow={Math.min(step, 5)} aria-label="Processing stations">
      <div className="rail__fill" style={{ width: `${Math.min(step, 4) * 20}%` }} />
      {STATIONS.map((s, i) => {
        const state = failed && i === step ? 'fail' : i < step || step >= 5 ? 'done' : i === step ? 'work' : '';
        return (
          <div key={s} className={`st ${state ? `st--${state}` : ''}`}>
            <span className="hole" />
            <span className="st__label">{s}</span>
          </div>
        );
      })}
    </div>
  );
}

function Card({ item, onDismiss }: { item: TrayItem; onDismiss: () => void }) {
  const done = item.step >= 5;
  const failed = !!item.error;
  const r = item.result ? RESULT[item.result] : null;
  const cleared = item.status === 'MATCHED';
  return (
    <div className="tray-card">
      <div className="tray-card__head">
        <span className="tray-card__file num" title={item.file}>{item.file}</span>
        <button type="button" className="icon-btn tray-card__close" aria-label={`Close ${item.file}`} title="Close" onClick={onDismiss}><X size={14} weight="bold" /></button>
      </div>
      <PunchRail step={item.step} failed={failed} />
      <div className="tray-card__foot">
        {failed ? (
          <span className="ink ink--bad">{item.error}</span>
        ) : done && r ? (
          <>
            <span>{cleared ? 'Cleared automatically' : item.status === 'DUPLICATE' ? 'Duplicate: not processed' : 'Sent to your in-tray'}</span>
            <Link href={`/app/invoices/${item.id}`} className={`minichip minichip--${r.tone}`}>{r.label}</Link>
          </>
        ) : (
          <span className="muted">{item.seen ? WORKING[Math.min(item.step, 4)] : 'Waiting in the queue…'}</span>
        )}
      </div>
    </div>
  );
}

const VISIBLE = 4;

export function ProcessingTray() {
  const { tray, dismiss, clear } = useRealtime();
  const { fx } = usePrefs();
  // newest first; show a few cards and summarise the rest
  const ordered = [...tray].reverse();
  const shown = ordered.slice(0, VISIBLE);
  const hidden = ordered.length - shown.length;
  const working = tray.filter((t) => t.step < 5 && !t.error).length;
  return (
    <aside className="intray" aria-label="Processing tray" aria-live="polite" hidden={tray.length === 0}>
      <header className="intray__head">
        <span className="label">Processing · {working} at work</span>
        <button type="button" className="intray__clear" onClick={clear} aria-label="Close all processing cards">
          <X size={12} weight="bold" aria-hidden /> Clear all
        </button>
      </header>
      <div className="intray__list">
      <AnimatePresence initial={false}>
        {shown.map((t) => (
          <motion.div
            key={t.id}
            initial={fx === 'off' ? false : { opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={fx === 'off' ? { opacity: 0 } : { opacity: 0, x: 40 }}
            transition={{ duration: 0.25 }}
          >
            <Card item={t} onDismiss={() => dismiss(t.id)} />
          </motion.div>
        ))}
      </AnimatePresence>
      </div>
      {hidden > 0 && <p className="intray__more">+{hidden} more in the tray · they keep processing</p>}
    </aside>
  );
}
