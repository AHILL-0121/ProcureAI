'use client';

import { use, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, ArrowsClockwise, Check, Copy as CopyIcon, FileText, Pause, Stack, X } from '@phosphor-icons/react';
import { MatchLens, VerdictStamp } from '@/components/MatchLens';
import { NoteDialog } from '@/components/NoteDialog';
import { Key, LedgerSkeleton, Money, Notice, StatusInk } from '@/components/ui';
import { get, patch, post } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { IN_FLIGHT, ISSUE_LABEL, SEVERITY_TONE, can, date, pct, time } from '@/lib/format';
import { useHotkeys } from '@/lib/hooks';
import { usePrefs } from '@/lib/prefs';
import { useRealtime } from '@/lib/realtime';
import { useToast } from '@/lib/toast';
import type { AuditEntry, InvoiceDetail } from '@/lib/types';

const FINAL = ['APPROVED', 'REJECTED'];

export default function InvoiceWorkspace({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const qc = useQueryClient();
  const { user } = useAuth();
  const { toast } = useToast();
  const { fx } = usePrefs();
  const { subscribe } = useRealtime();
  const [stacked, setStacked] = useState(true);
  const [view, setView] = useState<'copies' | 'scan'>('copies');
  const [dialog, setDialog] = useState<null | 'approve' | 'reject' | 'hold'>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [drop, setDrop] = useState(false);
  const [shake, setShake] = useState(0);
  const lastStatus = useRef<string | null>(null);

  const q = useQuery({
    queryKey: ['invoice', id],
    queryFn: () => get<InvoiceDetail>(`/invoices/${id}`),
    refetchInterval: (query) => (query.state.data && IN_FLIGHT.includes(query.state.data.status) ? 2000 : false),
  });
  const trail = useQuery({ queryKey: ['invoice', id, 'audit'], queryFn: () => get<AuditEntry[]>(`/invoices/${id}/audit`) });
  const inv = q.data;

  // Fan the copies out once the invoice has loaded, so the motion is seen
  useEffect(() => {
    if (!inv) return;
    const t = window.setTimeout(() => setStacked(false), fx === 'off' ? 0 : 450);
    return () => window.clearTimeout(t);
  }, [inv?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Drop a stamp when the verdict changes while the page is open
  useEffect(() => {
    if (!inv) return;
    if (lastStatus.current && lastStatus.current !== inv.status) {
      setDrop(true);
      setShake((n) => n + 1);
    }
    lastStatus.current = inv.status;
  }, [inv?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => subscribe((e) => {
    if (e.invoice_id === id) {
      qc.invalidateQueries({ queryKey: ['invoice', id] });
    }
  }), [subscribe, id, qc]);

  useHotkeys({ c: () => view === 'copies' && setStacked((s) => !s) }, [view]);

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ['invoice', id] });
    qc.invalidateQueries({ queryKey: ['invoices'] });
    qc.invalidateQueries({ queryKey: ['stats'] });
  };

  const act = async (label: string, fn: () => Promise<unknown>, success?: string) => {
    setBusy(label);
    try {
      await fn();
      refresh();
      if (success) toast(success);
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Action failed', { tone: 'error' });
    } finally {
      setBusy(null);
    }
  };

  if (q.isLoading) return <div className="screen"><LedgerSkeleton rows={8} /></div>;
  if (q.isError || !inv) {
    return <div className="screen"><Notice tone="bad">{(q.error as Error)?.message ?? 'Invoice not found'}</Notice></div>;
  }

  const processing = IN_FLIGHT.includes(inv.status);
  const final = FINAL.includes(inv.status);
  const editable = can.edit(user?.role) && !final && !processing;
  const hasHigh = (inv.discrepancies ?? []).some((d) => d.severity === 'HIGH');
  const decidable = ['MATCHED', 'DISCREPANCY', 'ON_HOLD'].includes(inv.status);

  return (
    <div className="screen ws">
      <div className="ws__top">
        <Link href="/app/in-tray" className="back"><ArrowLeft size={14} aria-hidden /> In-tray</Link>
        <StatusInk status={inv.status} />
      </div>

      <div className="ws__title">
        <div>
          <p className="label">{inv.invoice_type === 'STANDARD' ? 'Invoice' : inv.invoice_type.replace('_', ' ').toLowerCase()} · received {date(inv.created_at)}{inv.source_email && inv.source_email !== 'upload' ? ` from ${inv.source_email}` : ''}</p>
          <h1 className="display">{inv.invoice_number ?? inv.original_filename ?? 'Unread invoice'}</h1>
          <p className="ws__meta"><span>{inv.vendor_name ?? 'Unknown vendor'}</span><Money amount={inv.total_amount} currency={inv.currency} /></p>
        </div>
      </div>

      {processing && (
        <Notice>This invoice is still being processed. The page updates on its own.</Notice>
      )}
      {inv.status === 'FAILED' && (
        <Notice tone="bad">
          <b>Could not read this document.</b> {inv.error}
          {can.edit(user?.role) && (
            <Key size="sm" className="notice__action" busy={busy === 'retry'} onClick={() => act('retry', () => post(`/invoices/${id}/retry`), 'Sent back to the tray')}>
              <ArrowsClockwise size={14} /> Try again
            </Key>
          )}
        </Notice>
      )}
      {inv.status === 'DUPLICATE' && inv.duplicate_of && (
        <Notice tone="bad">This invoice number was already received from this vendor. <Link href={`/app/invoices/${inv.duplicate_of}`}>Open the original</Link>.</Notice>
      )}

      <div className="ws__grid">
        <div className="ws__main">
          <div className="lens-bar">
            <div className="seg seg--tabs" role="tablist" aria-label="View">
              <button role="tab" type="button" aria-selected={view === 'copies'} onClick={() => setView('copies')}><Stack size={14} /> Copies</button>
              <button role="tab" type="button" aria-selected={view === 'scan'} onClick={() => setView('scan')}><FileText size={14} /> Scan</button>
            </div>
            {view === 'copies' && (
              <Key size="sm" variant="ghost" className="hide-mobile" onClick={() => setStacked((s) => !s)}>
                <CopyIcon size={14} /> {stacked ? 'Compare copies' : 'Stack copies'} <kbd>C</kbd>
              </Key>
            )}
            <p className="muted lens-bar__hint hide-mobile">Invoice, purchase order and goods receipt, lined up by matched line.</p>
          </div>

          {view === 'copies' ? (
            <div className={`lens-wrap ${shake ? 'shake' : ''}`} key={shake}>
              <MatchLens invoice={inv} stacked={stacked} stamp={<VerdictStamp invoice={inv} drop={drop} />} />
            </div>
          ) : (
            <ScanViewer id={id} />
          )}

          {decidable && (can.edit(user?.role)) && (
            <div className="actions">
              <div>
                {can.decide(user?.role) && <Key variant="danger" onClick={() => setDialog('reject')} busy={busy === 'reject'}><X size={15} weight="bold" /> Reject</Key>}
                {inv.status !== 'ON_HOLD' && <Key onClick={() => setDialog('hold')} busy={busy === 'hold'}><Pause size={15} weight="bold" /> Hold</Key>}
              </div>
              <div>
                <Key variant={edited(inv) ? 'primary' : 'plain'} busy={busy === 'rematch'} onClick={() => act('rematch', () => post(`/invoices/${id}/rematch`), 'Re-matched with the current fields')}>
                  <ArrowsClockwise size={15} /> Re-match
                </Key>
                {can.decide(user?.role) && (
                  <Key variant="primary" busy={busy === 'approve'} onClick={() => (hasHigh ? setDialog('approve') : act('approve', () => post(`/invoices/${id}/approve`, {}), 'Approved and cleared for payment'))}>
                    <Check size={15} weight="bold" /> Approve
                  </Key>
                )}
              </div>
            </div>
          )}
          {final && can.edit(user?.role) && inv.reviewed_by && (
            <div className="actions actions--final">
              <span className="muted">{inv.status === 'APPROVED' ? 'Approved' : 'Rejected'} by {inv.reviewed_by} · {date(inv.reviewed_at)} {time(inv.reviewed_at)}{inv.review_note ? ` — “${inv.review_note}”` : ''}</span>
              <Key size="sm" variant="ghost" busy={busy === 'reopen'} onClick={() => act('reopen', () => post(`/invoices/${id}/reopen`), 'Decision undone')}>Undo decision</Key>
            </div>
          )}
        </div>

        <aside className="ws__side">
          <Checks inv={inv} />
          <Fields inv={inv} editable={editable} onSaved={refresh} />
          <Timeline entries={trail.data ?? []} />
        </aside>
      </div>

      <NoteDialog
        open={dialog === 'reject'}
        onOpenChange={(v) => !v && setDialog(null)}
        title="Reject this invoice"
        description="The supplier will need to resend. Say why, for the audit trail."
        confirmLabel="Reject"
        tone="danger"
        onConfirm={(note) => act('reject', () => post(`/invoices/${id}/reject`, { note }), 'Rejected')}
      />
      <NoteDialog
        open={dialog === 'approve'}
        onOpenChange={(v) => !v && setDialog(null)}
        title="Approve over an exception"
        description={`High-severity issue: ${inv.top_issue ?? ''}. Explain why it is acceptable.`}
        confirmLabel="Approve anyway"
        tone="primary"
        onConfirm={(note) => act('approve', () => post(`/invoices/${id}/approve`, { note }), 'Approved with an override note')}
      />
      <NoteDialog
        open={dialog === 'hold'}
        onOpenChange={(v) => !v && setDialog(null)}
        title="Put on hold"
        description="For example: waiting on a credit note, or on the warehouse to post the receipt."
        confirmLabel="Hold"
        required={false}
        onConfirm={(note) => act('hold', () => post(`/invoices/${id}/hold`, { note: note || null }), 'On hold')}
      />
    </div>
  );
}

function edited(inv: InvoiceDetail) {
  return !!inv.validation?.edited_fields && Object.keys(inv.validation.edited_fields).length > 0;
}

function ScanViewer({ id }: { id: string }) {
  const link = useQuery({
    queryKey: ['doc', id],
    queryFn: () => get<{ url: string; media_type: string; filename: string | null }>(`/invoices/${id}/document-link`),
    staleTime: 8 * 60_000,
  });
  const text = useQuery({
    queryKey: ['doc-text', id, link.data?.url],
    queryFn: () => fetch(link.data!.url).then((r) => r.text()),
    enabled: !!link.data && link.data.media_type.startsWith('text/'),
  });
  if (link.isLoading) return <div className="scan"><LedgerSkeleton rows={10} /></div>;
  if (link.isError || !link.data) return <Notice tone="bad">{(link.error as Error)?.message ?? 'No document stored'}</Notice>;
  const { url, media_type, filename } = link.data;
  return (
    <div className="scan sheet sheet--white">
      <div className="scan__bar">
        <span className="num muted">{filename}</span>
        <a href={url} target="_blank" rel="noreferrer" className="linkish">Open in a new tab</a>
      </div>
      {media_type === 'application/pdf' ? (
        <iframe src={url} title={filename ?? 'Invoice document'} className="scan__frame" />
      ) : media_type.startsWith('image/') ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={url} alt={`Scan of ${filename ?? 'the invoice'}`} className="scan__img" />
      ) : (
        <pre className="scan__text num">{text.data ?? 'Loading…'}</pre>
      )}
    </div>
  );
}

function Checks({ inv }: { inv: InvoiceDetail }) {
  const failed = inv.discrepancies ?? [];
  const passed = (inv.match_checks ?? []).filter((c) => c.passed);
  const warnings = inv.validation?.warnings ?? [];
  const [showPassed, setShowPassed] = useState(false);
  return (
    <section className="sheet panel">
      <h2 className="label">Checks</h2>
      {failed.length === 0 && inv.match_result === 'FULL_MATCH' && <p className="ink ink--ok">Every check passed.</p>}
      {failed.length === 0 && inv.match_result === 'PENDING' && <p className="muted">Not matched yet.</p>}
      <ul className="checks">
        {failed.map((d, i) => (
          <li key={i} className={`check check--${SEVERITY_TONE[d.severity]}`}>
            <StatusInk tone={SEVERITY_TONE[d.severity]} label={ISSUE_LABEL[d.type] ?? d.type} />
            <p>{d.message}</p>
          </li>
        ))}
      </ul>
      {passed.length > 0 && (
        <button type="button" className="linkish" onClick={() => setShowPassed((s) => !s)} aria-expanded={showPassed}>
          {showPassed ? 'Hide' : 'Show'} {passed.length} passed check{passed.length > 1 ? 's' : ''}
        </button>
      )}
      {showPassed && (
        <ul className="checks checks--passed">
          {passed.map((c, i) => <li key={i} className="check"><StatusInk tone={c.code.startsWith('PO_LINE') ? 'pencil' : 'ok'} label={c.message} /></li>)}
        </ul>
      )}
      {warnings.length > 0 && (
        <details className="warnings">
          <summary className="linkish">{warnings.length} reading note{warnings.length > 1 ? 's' : ''}</summary>
          <ul>{warnings.map((w, i) => <li key={i} className="muted">{w}</li>)}</ul>
        </details>
      )}
      {inv.extraction && (
        <p className="muted small">
          Read by {inv.extraction.extraction_method?.replace('_', ' ')}{inv.extraction.ocr_confidence != null ? ` (OCR ${inv.extraction.ocr_confidence}%)` : ''} · confidence {pct(inv.confidence_score)}
          {inv.extraction.totals_found_in_text === false && <span className="ink ink--hold"> · total not found in the document text</span>}
        </p>
      )}
    </section>
  );
}

const FIELD_DEFS: { key: keyof InvoiceDetail; label: string; type?: string; mono?: boolean }[] = [
  { key: 'invoice_number', label: 'Invoice', mono: true },
  { key: 'vendor_name', label: 'Vendor' },
  { key: 'vendor_tax_id', label: 'Tax ID', mono: true },
  { key: 'invoice_date', label: 'Date', type: 'date', mono: true },
  { key: 'po_reference', label: 'PO', mono: true },
  { key: 'currency', label: 'Currency', mono: true },
  { key: 'subtotal', label: 'Subtotal', type: 'number', mono: true },
  { key: 'tax_amount', label: 'Tax', type: 'number', mono: true },
  { key: 'total_amount', label: 'Total', type: 'number', mono: true },
];

function Fields({ inv, editable, onSaved }: { inv: InvoiceDetail; editable: boolean; onSaved: () => void }) {
  const { toast } = useToast();
  const [draft, setDraft] = useState<Record<string, string>>({});
  const edits = inv.validation?.edited_fields ?? {};

  const save = async (key: string, type?: string) => {
    if (!(key in draft)) return;
    const raw = draft[key].trim();
    const original = inv[key as keyof InvoiceDetail];
    if (String(original ?? '') === raw) return;
    let value: string | number | null = raw === '' ? null : raw;
    if (type === 'number' && value !== null) {
      value = Number(String(value).replace(/,/g, ''));
      if (Number.isNaN(value)) {
        toast('Enter a number', { tone: 'error' });
        return;
      }
    }
    if (key === 'currency' && typeof value === 'string') value = value.toUpperCase();
    try {
      await patch(`/invoices/${inv.id}`, { [key]: value });
      toast('Saved. Re-match to check it again.');
      setDraft((d) => { const n = { ...d }; delete n[key]; return n; });
      onSaved();
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Could not save', { tone: 'error' });
    }
  };

  return (
    <section className="sheet panel">
      <h2 className="label">Extracted fields</h2>
      <div className="fields">
        {FIELD_DEFS.map((f) => {
          const val = draft[f.key as string] ?? String(inv[f.key] ?? '');
          const id = `field-${String(f.key)}`;
          return (
            <div className="field" key={String(f.key)}>
              <label className="label" htmlFor={id}>{f.label}</label>
              <div className="field__val">
                <input
                  id={id}
                  className={f.mono ? 'num' : undefined}
                  type={f.type === 'date' ? 'date' : 'text'}
                  inputMode={f.type === 'number' ? 'decimal' : undefined}
                  value={val}
                  readOnly={!editable}
                  maxLength={f.key === 'currency' ? 3 : undefined}
                  onChange={(e) => setDraft((d) => ({ ...d, [f.key]: e.target.value }))}
                  onBlur={() => editable && save(String(f.key), f.type)}
                  onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }}
                />
                {edits[String(f.key)] && <span className="edited hand" title={`Edited by ${edits[String(f.key)]}`}>✎</span>}
              </div>
            </div>
          );
        })}
      </div>
      {editable && <p className="muted small">Click a value to correct it. Changes are logged.</p>}
    </section>
  );
}

const ACTION_TEXT: Record<string, string> = {
  RECEIVED: 'Received', EXTRACTION_COMPLETE: 'Read', VALIDATION_COMPLETE: 'Checked', MATCH_COMPLETE: 'Matched',
  DUPLICATE_DETECTED: 'Flagged as duplicate', PROCESSING_FAILED: 'Could not read', FIELDS_EDITED: 'Fields corrected',
  REMATCH_REQUESTED: 'Re-match requested', APPROVED: 'Approved', APPROVED_OVERRIDE: 'Approved over an exception',
  REJECTED: 'Rejected', HELD: 'Put on hold', REOPENED: 'Decision undone', RETRY: 'Retry requested',
};

function Timeline({ entries }: { entries: AuditEntry[] }) {
  return (
    <section className="sheet panel">
      <h2 className="label">Timeline</h2>
      <ol className="tl">
        {entries.map((e) => {
          const d = e.details ?? {};
          const detail =
            e.action === 'MATCH_COMPLETE' ? `${String(d.result ?? '').replace('_', ' ').toLowerCase()} · score ${d.score ?? '—'}` :
            e.action === 'EXTRACTION_COMPLETE' ? `${String(d.extraction_method ?? '').replace('_', ' ')} · ${pct(Number(d.confidence_score ?? 0))} confident` :
            e.action === 'FIELDS_EDITED' ? Object.keys(d).join(', ') :
            e.action === 'PROCESSING_FAILED' ? String(d.error ?? '') :
            typeof d.note === 'string' && d.note ? `“${d.note}”` : '';
          return (
            <li key={e.id} className={e.actor ? 'is-human' : ''}>
              <span className="num">{time(e.timestamp)}</span>
              <span>
                {ACTION_TEXT[e.action] ?? e.action.toLowerCase().replace(/_/g, ' ')}
                {e.actor && <span className="muted"> · {e.actor.split('@')[0]}</span>}
                {detail && <span className="tl__detail muted">{detail}</span>}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
