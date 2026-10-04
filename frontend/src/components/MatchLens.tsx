'use client';

import { PencilCircle, Stamp } from '@/components/ui';
import { date, money, qty, signedPct } from '@/lib/format';
import type { InvoiceDetail, MatchLine, POLine } from '@/lib/types';

interface AlignedRow {
  key: string;
  inv: MatchLine | null;
  po: POLine | null;
}

function align(inv: InvoiceDetail): AlignedRow[] {
  const snap = inv.match_snapshot;
  const poLines = snap?.po?.lines ?? [];
  const byId = new Map(poLines.map((l) => [l.po_line_id, l]));
  const rows: AlignedRow[] = [];
  const used = new Set<string>();
  const lines: MatchLine[] = snap?.lines?.length
    ? snap.lines
    : inv.line_items.map((l) => ({ line: l.line_no, description: l.description, item_code: l.item_code, quantity: l.quantity,
      unit_price: l.unit_price, total_price: l.total_price, po_line_id: l.matched_po_line_id, checks: [] }));
  for (const l of lines) {
    const po = l.po_line_id ? byId.get(l.po_line_id) ?? null : null;
    if (po) used.add(po.po_line_id);
    rows.push({ key: `i${l.line}`, inv: l, po });
  }
  for (const p of poLines) if (!used.has(p.po_line_id)) rows.push({ key: `p${p.po_line_id}`, inv: null, po: p });
  return rows;
}

export function MatchLens({ invoice, stacked, stamp }: { invoice: InvoiceDetail; stacked: boolean; stamp?: React.ReactNode }) {
  const snap = invoice.match_snapshot;
  const po = snap?.po ?? null;
  const rows = align(invoice);
  const tol = snap?.tolerance;

  return (
    <div className={`lens ${stacked ? 'is-stacked' : ''}`}>
      {/* Invoice — white original */}
      <article className="copy copy--white">
        <header className="copy__tag">
          <span className="label">Original · Invoice</span>
          <span className="num">{invoice.invoice_number ?? '—'}</span>
        </header>
        <h3 className="display copy__title">{invoice.vendor_name ?? 'Unknown vendor'}</h3>
        {stamp}
        {rows.map((r) => (
          <div className="ln3" key={r.key}>
            <span className="ln3__n num">{r.inv ? r.inv.line : '–'}</span>
            {r.inv ? (
              <>
                <span className="ln3__d">{r.inv.description || r.inv.item_code || 'Line'}</span>
                <span className="ln3__m">
                  <Cell issue={r.inv.checks.some((c) => c.startsWith('QTY_'))} note={r.inv.checks.includes('QTY_EXCEEDS_RECEIVED') ? `only ${qty(Math.max(r.inv.available_qty ?? 0, 0))} due` : undefined} stacked={stacked}>
                    <span className="num">{qty(r.inv.quantity)}</span>
                  </Cell>
                  {' @ '}
                  <Cell issue={r.inv.checks.includes('PRICE_OVER')} note={signedPct(r.inv.price_variance_pct)} stacked={stacked}>
                    <span className="num">{money(r.inv.unit_price)}</span>
                  </Cell>
                  {r.inv.checks.includes('UNMATCHED_LINE') && <span className="pencil__note hand pencil--bad"> not on the PO</span>}
                </span>
              </>
            ) : (
              <span className="ln3__d muted">not invoiced</span>
            )}
          </div>
        ))}
        <footer className="copy__total">
          <span>Total</span>
          <span className="num">{money(invoice.total_amount, invoice.currency)}</span>
        </footer>
      </article>

      {/* Purchase order — canary copy */}
      <article className="copy copy--canary" aria-hidden={stacked || undefined}>
        <div className="copy__body">
          <header className="copy__tag">
            <span className="label">Purchase order copy</span>
            <span className="num">{po?.po_number ?? invoice.po_reference ?? '—'}</span>
          </header>
          <h3 className="display copy__title">{po ? `Ordered ${date(po.order_date)}` : 'No purchase order'}</h3>
          {po ? rows.map((r) => (
            <div className="ln3" key={r.key}>
              <span className="ln3__n num">{r.po ? r.po.line_num : '–'}</span>
              {r.po ? (
                <>
                  <span className="ln3__d">{r.po.description}<span className="muted num"> · {r.po.item_number}</span></span>
                  <span className="ln3__m"><span className="num">{qty(r.po.quantity)} {r.po.uom}</span> @ <span className="num">{money(r.po.unit_price)}</span></span>
                </>
              ) : <span className="ln3__d muted">not on this PO</span>}
            </div>
          )) : <p className="copy__empty hand">{invoice.po_reference ? `${invoice.po_reference} is not in the ERP` : 'The invoice quotes no PO number'}</p>}
          <footer className="copy__total">
            <span>PO value</span>
            <span className="num">{po ? money(po.total_amount, po.currency) : '—'}</span>
          </footer>
        </div>
      </article>

      {/* Goods receipt — pink copy */}
      <article className="copy copy--pink" aria-hidden={stacked || undefined}>
        <div className="copy__body">
          <header className="copy__tag">
            <span className="label">Receiving copy · GRN</span>
            <span className="num">{snap?.grn?.grn_number ?? '—'}</span>
          </header>
          <h3 className="display copy__title">{snap?.grn ? `Warehouse · ${snap.grn.status === 'COMPLETE' ? 'all lines' : `${snap.grn.lines_received} of ${snap.grn.lines_total} lines`}` : 'Nothing received'}</h3>
          {po ? rows.map((r) => {
            const received = r.po?.received_qty ?? 0;
            const billedLine = !!r.inv;
            return (
              <div className="ln3" key={r.key}>
                <span className="ln3__n num">{r.po ? r.po.line_num : '–'}</span>
                {r.po ? (
                  <>
                    <span className="ln3__d">{r.po.description}</span>
                    <span className="ln3__m">
                      {received > 0 ? (
                        <span className="ink ink--ok">✓ <span className="num">{qty(received)} {r.po.uom}</span> · {date(r.po.receipts.at(-1)?.date ?? null, { day: '2-digit', month: 'short' })}</span>
                      ) : billedLine ? (
                        <Cell issue note="billed, not received" stacked={stacked}><span className="ink ink--bad">Not received</span></Cell>
                      ) : (
                        <><span className="ink ink--pencil">Not received</span><span className="pencil__note hand pencil--grey"> not billed, so not held</span></>
                      )}
                    </span>
                  </>
                ) : <span className="ln3__d muted">—</span>}
              </div>
            );
          }) : <p className="copy__empty hand">No PO, so no receipt to compare</p>}
          <footer className="copy__total">
            <span>Received</span>
            <span className="num">{snap?.grn ? `${snap.grn.lines_received} of ${snap.grn.lines_total} lines` : '0 lines'}</span>
          </footer>
        </div>
      </article>

      {tol && (
        <p className="lens__tol muted">
          Tolerances: price ±{(tol.price_pct * 100).toFixed(0)}% (min {tol.price_abs.toFixed(2)}), quantity ±{(tol.qty_pct * 100).toFixed(0)}%.
        </p>
      )}
    </div>
  );
}

function Cell({ issue, note, stacked, children }: { issue: boolean; note?: string; stacked: boolean; children: React.ReactNode }) {
  if (!issue) return <>{children}</>;
  return <PencilCircle note={note} active={!stacked}>{children}</PencilCircle>;
}

export function verdictStamp(inv: InvoiceDetail): { text: string; sub?: string; tone: 'ok' | 'hold' | 'bad' } | null {
  const who = inv.reviewed_by ? inv.reviewed_by.split('@')[0].slice(0, 3).toUpperCase() : 'AUTO';
  const when = inv.reviewed_at ? date(inv.reviewed_at, { day: '2-digit', month: 'short', year: 'numeric' }).toUpperCase() : undefined;
  switch (inv.status) {
    case 'APPROVED': return { text: 'Approved', sub: `${when ?? ''} · ${who}`, tone: 'ok' };
    case 'REJECTED': return { text: 'Rejected', sub: `${when ?? ''} · ${who}`, tone: 'bad' };
    case 'ON_HOLD': return { text: 'On hold', sub: inv.reviewed_by ? `${when} · ${who}` : 'Awaiting receipt', tone: 'hold' };
    case 'MATCHED': return { text: 'Matched', sub: 'Auto · 3-way', tone: 'ok' };
    case 'DISCREPANCY': return { text: 'Exception', sub: 'Needs review', tone: 'hold' };
    case 'DUPLICATE': return { text: 'Duplicate', tone: 'bad' };
    default: return null;
  }
}

export function VerdictStamp({ invoice, drop }: { invoice: InvoiceDetail; drop: boolean }) {
  const v = verdictStamp(invoice);
  if (!v) return null;
  return <Stamp key={`${invoice.status}`} text={v.text} sub={v.sub} tone={v.tone} drop={drop} seed={invoice.id.charCodeAt(0) + invoice.status.length} className="copy__stamp" />;
}
