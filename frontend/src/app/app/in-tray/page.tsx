'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { AnimatePresence, motion } from 'motion/react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, Pause, Rows, X } from '@phosphor-icons/react';
import { NoteDialog } from '@/components/NoteDialog';
import { Blot, EmptyTray, Hl, LedgerSkeleton, Money, Notice, StatusInk } from '@/components/ui';
import { get, post, qs } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { ISSUE_LABEL, SEVERITY_TONE, age, can } from '@/lib/format';
import { useHotkeys } from '@/lib/hooks';
import { usePrefs } from '@/lib/prefs';
import { useToast } from '@/lib/toast';
import type { InvoiceDetail, InvoiceSummary, Page } from '@/lib/types';

const FILTERS = [
  { key: 'all', label: 'All', issue: undefined },
  { key: 'price', label: 'Price', issue: 'PRICE_OVER' },
  { key: 'qty', label: 'Quantity', issue: 'QTY_EXCEEDS_RECEIVED,QTY_EXCEEDS_PO,UOM_MISMATCH' },
  { key: 'receipt', label: 'No receipt', issue: 'NOT_RECEIVED' },
  { key: 'vendor', label: 'Vendor', issue: 'VENDOR_MISMATCH,VENDOR_UNVERIFIED' },
  { key: 'currency', label: 'Currency', issue: 'CURRENCY_MISMATCH,CURRENCY_MISSING' },
  { key: 'po', label: 'PO & lines', issue: 'MISSING_PO,MISSING_PO_REFERENCE,UNMATCHED_LINE,PO_CLOSED,TOTAL_MISMATCH' },
  { key: 'reading', label: 'Reading', issue: 'VALIDATION_ERROR,LOW_CONFIDENCE,NO_LINES' },
] as const;

type Pending = { kind: 'approve' | 'reject' | 'hold'; inv: InvoiceSummary } | null;

export default function InTrayPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { toast } = useToast();
  const { user } = useAuth();
  const { fx, density, setDensity } = usePrefs();
  const [filter, setFilter] = useState<(typeof FILTERS)[number]['key']>('all');
  const [pageSize, setPageSize] = useState(25);
  const [cursor, setCursor] = useState(0);
  const [leaving, setLeaving] = useState<Set<string>>(new Set());
  const [pending, setPending] = useState<Pending>(null);
  const rowRefs = useRef<(HTMLDivElement | null)[]>([]);
  const issue = FILTERS.find((f) => f.key === filter)?.issue;

  const q = useQuery({
    queryKey: ['invoices', 'review', filter, pageSize],
    queryFn: () => get<Page<InvoiceSummary>>(`/invoices${qs({ queue: 'review', issue, page_size: pageSize, sort: '-created_at' })}`),
  });
  const rows = useMemo(() => (q.data?.items ?? []).filter((r) => !leaving.has(r.id)), [q.data, leaving]);

  useEffect(() => {
    setCursor((c) => Math.min(c, Math.max(0, rows.length - 1)));
  }, [rows.length]);

  const refresh = useCallback(() => {
    qc.invalidateQueries({ queryKey: ['invoices'] });
    qc.invalidateQueries({ queryKey: ['stats'] });
  }, [qc]);

  const undo = useCallback(async (id: string) => {
    try {
      await post<InvoiceDetail>(`/invoices/${id}/reopen`);
      setLeaving((s) => { const n = new Set(s); n.delete(id); return n; });
      refresh();
      toast('Put back in the in-tray');
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Could not undo', { tone: 'error' });
    }
  }, [refresh, toast]);

  const decide = useCallback(async (inv: InvoiceSummary, kind: 'approve' | 'reject' | 'hold', note?: string) => {
    const path = { approve: 'approve', reject: 'reject', hold: 'hold' }[kind];
    await post<InvoiceDetail>(`/invoices/${inv.id}/${path}`, { note: note || null });
    const label = inv.invoice_number || inv.original_filename || 'Invoice';
    if (kind === 'hold') {
      toast(`${label} put on hold`, { action: { label: 'Undo', run: () => undo(inv.id) } });
      refresh();
      return;
    }
    setLeaving((s) => new Set(s).add(inv.id));
    toast(`${label} ${kind === 'approve' ? 'approved and cleared' : 'rejected'}`, {
      action: { label: 'Put it back', run: () => undo(inv.id) },
    });
    window.setTimeout(refresh, 700);
  }, [refresh, toast, undo]);

  const request = useCallback((inv: InvoiceSummary, kind: 'approve' | 'reject' | 'hold') => {
    if (kind === 'reject' || (kind === 'approve' && inv.top_issue_severity === 'HIGH')) {
      setPending({ kind, inv });
      return;
    }
    decide(inv, kind).catch((e) => toast(e instanceof Error ? e.message : 'Action failed', { tone: 'error' }));
  }, [decide, toast]);

  const focusRow = (i: number) => {
    setCursor(i);
    rowRefs.current[i]?.focus();
  };

  useHotkeys({
    j: () => rows.length && focusRow(Math.min(cursor + 1, rows.length - 1)),
    k: () => rows.length && focusRow(Math.max(cursor - 1, 0)),
    a: () => rows[cursor] && can.decide(user?.role) && request(rows[cursor], 'approve'),
    r: () => rows[cursor] && can.decide(user?.role) && request(rows[cursor], 'reject'),
    h: () => rows[cursor] && can.edit(user?.role) && rows[cursor].status !== 'ON_HOLD' && request(rows[cursor], 'hold'),
  }, [rows, cursor, user, request]);

  const total = q.data?.total ?? 0;

  return (
    <div className="screen">
      <div className="screen__head">
        <div>
          <p className="label">Exceptions waiting for a decision</p>
          <h1 className="display screen__title">In-tray <span className="screen__count num">{total}</span></h1>
        </div>
        <button type="button" className="key key--ghost key--sm" aria-pressed={density === 'ledger'} onClick={() => setDensity(density === 'ledger' ? 'comfortable' : 'ledger')}>
          <Rows size={15} aria-hidden /> {density === 'ledger' ? 'Comfortable rows' : 'Ledger rows'}
        </button>
      </div>

      <div className="sheet sheet--flush">
        <div className="ptabs" role="group" aria-label="Filter by reason">
          {FILTERS.map((f) => (
            <button key={f.key} type="button" className="ptab" aria-pressed={filter === f.key} onClick={() => { setFilter(f.key); setCursor(0); }}>
              {f.label}
            </button>
          ))}
        </div>

        <div className="ledger" role="table" aria-label="Invoices waiting for review" aria-rowcount={rows.length}>
          <div className="ledger__head tray-grid" role="row">
            <span role="columnheader"><span className="sr-only">Severity</span></span>
            <span role="columnheader" className="label">Invoice</span>
            <span role="columnheader" className="label col-vendor">Vendor</span>
            <span role="columnheader" className="label col-po">PO</span>
            <span role="columnheader" className="label ta-r">Amount</span>
            <span role="columnheader" className="label col-why">Why it&apos;s here</span>
            <span role="columnheader" className="label ta-r col-age">Age</span>
            <span role="columnheader" className="label stub-head">Decide</span>
          </div>

          {q.isLoading && <LedgerSkeleton />}
          {q.isError && <div className="pad"><Notice tone="bad">{(q.error as Error).message}</Notice></div>}
          {q.isSuccess && rows.length === 0 && (
            <EmptyTray title={filter === 'all' ? 'In-tray empty.' : 'Nothing under this tab.'}>
              {filter === 'all' ? 'Nicely done. New exceptions land here as invoices are read.' : 'Try another reason, or All.'}
            </EmptyTray>
          )}

          <AnimatePresence initial={false}>
            {rows.map((r, i) => (
              <motion.div
                key={r.id}
                layout={fx !== 'off'}
                role="row"
                tabIndex={0}
                ref={(el) => { rowRefs.current[i] = el; }}
                className={`row tray-grid ${i === cursor ? 'is-cursor' : ''}`}
                onFocus={() => setCursor(i)}
                onClick={() => router.push(`/app/invoices/${r.id}`)}
                onKeyDown={(e) => { if (e.key === 'Enter' && e.currentTarget === e.target) router.push(`/app/invoices/${r.id}`); }}
                exit={fx === 'full' ? { x: 24, y: 30, rotate: -2.5, opacity: 0, transition: { duration: 0.42 } } : { opacity: 0, transition: { duration: 0.2 } }}
              >
                <span role="cell"><Blot severity={r.top_issue_severity} /></span>
                <span role="cell" className="cell-inv">
                  <Link href={`/app/invoices/${r.id}`} className="num inv-link" onClick={(e) => e.stopPropagation()}>
                    <Hl>{r.invoice_number || r.original_filename || 'Unread invoice'}</Hl>
                  </Link>
                  <small className="muted mobile-only">{r.vendor_name}</small>
                </span>
                <span role="cell" className="col-vendor ellipsis">{r.vendor_name || '—'}</span>
                <span role="cell" className="col-po num muted">{r.po_reference || '—'}</span>
                <span role="cell" className="ta-r"><Hl><Money amount={r.total_amount} currency={r.currency} /></Hl></span>
                <span role="cell" className="col-why" title={r.top_issue ?? undefined}>
                  {r.status === 'ON_HOLD' && r.reviewed_by ? (
                    <StatusInk tone="hold" label={`On hold · ${r.reviewed_by.split('@')[0]}`} />
                  ) : r.top_issue_code ? (
                    <StatusInk tone={SEVERITY_TONE[r.top_issue_severity ?? 'LOW']} label={`${ISSUE_LABEL[r.top_issue_code] ?? r.top_issue_code}${r.issue_count > 1 ? ` +${r.issue_count - 1}` : ''}`} />
                  ) : (
                    <StatusInk status={r.status} />
                  )}
                </span>
                <span role="cell" className="ta-r col-age num muted">{age(r.created_at)}</span>
                <span role="cell" className="stub" onClick={(e) => e.stopPropagation()}>
                  {can.decide(user?.role) && (
                    <button type="button" className="sbtn sbtn--ok" aria-label={`Approve ${r.invoice_number ?? ''}`} title="Approve (A)" onClick={() => request(r, 'approve')}><Check weight="bold" /></button>
                  )}
                  {can.edit(user?.role) && r.status !== 'ON_HOLD' && (
                    <button type="button" className="sbtn sbtn--hold" aria-label={`Hold ${r.invoice_number ?? ''}`} title="Hold (H)" onClick={() => request(r, 'hold')}><Pause weight="bold" /></button>
                  )}
                  {can.decide(user?.role) && (
                    <button type="button" className="sbtn sbtn--bad" aria-label={`Reject ${r.invoice_number ?? ''}`} title="Reject (R)" onClick={() => request(r, 'reject')}><X weight="bold" /></button>
                  )}
                </span>
              </motion.div>
            ))}
          </AnimatePresence>

          {total > rows.length + leaving.size && (
            <div className="ledger__more">
              <button type="button" className="key key--plain key--sm" onClick={() => setPageSize((n) => n + 25)}>Show 25 more</button>
            </div>
          )}
          <div className="kbd-help">
            <span><kbd>J</kbd> <kbd>K</kbd> move</span>
            <span><kbd>Enter</kbd> open</span>
            {can.decide(user?.role) && <span><kbd>A</kbd> approve</span>}
            {can.edit(user?.role) && <span><kbd>H</kbd> hold</span>}
            {can.decide(user?.role) && <span><kbd>R</kbd> reject</span>}
          </div>
        </div>
      </div>

      <NoteDialog
        open={!!pending}
        onOpenChange={(v) => !v && setPending(null)}
        title={pending?.kind === 'reject' ? `Reject ${pending.inv.invoice_number ?? 'invoice'}` : `Override and approve ${pending?.inv.invoice_number ?? ''}`}
        description={pending?.kind === 'reject'
          ? 'The supplier will need to resend. Say why, for the audit trail.'
          : pending ? `This invoice has a high-severity issue: ${pending.inv.top_issue ?? ''}` : undefined}
        confirmLabel={pending?.kind === 'reject' ? 'Reject' : 'Approve anyway'}
        tone={pending?.kind === 'reject' ? 'danger' : 'primary'}
        onConfirm={async (note) => { if (pending) await decide(pending.inv, pending.kind, note); }}
      />
    </div>
  );
}
