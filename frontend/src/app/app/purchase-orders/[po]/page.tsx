'use client';

import { use } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft } from '@phosphor-icons/react';
import { LedgerSkeleton, Money, Notice, StatusInk } from '@/components/ui';
import { get } from '@/lib/api';
import { date, money, qty } from '@/lib/format';
import type { GoodsReceipt, InvoiceSummary, PurchaseOrder } from '@/lib/types';

export default function PODetail({ params }: { params: Promise<{ po: string }> }) {
  const { po: poNumber } = use(params);
  const q = useQuery({
    queryKey: ['po', poNumber],
    queryFn: () => get<{ purchase_order: PurchaseOrder; goods_receipt: GoodsReceipt | null; invoices: InvoiceSummary[] }>(`/purchase-orders/${poNumber}`),
  });
  if (q.isLoading) return <div className="screen"><LedgerSkeleton rows={6} /></div>;
  if (q.isError || !q.data) return <div className="screen"><Notice tone="bad">{(q.error as Error)?.message}</Notice></div>;
  const { purchase_order: po, goods_receipt: grn, invoices } = q.data;

  return (
    <div className="screen">
      <div className="ws__top">
        <Link href="/app/purchase-orders" className="back"><ArrowLeft size={14} aria-hidden /> Purchase orders</Link>
      </div>
      <div className="ws__title">
        <div>
          <p className="label">Purchase order · ordered {date(po.order_date)} · {po.status.toLowerCase()}</p>
          <h1 className="display">{po.po_number}</h1>
          <p className="ws__meta"><span>{po.vendor_name}</span><span className="num muted">{po.vendor_tax_id}</span><Money amount={po.total_amount} currency={po.currency} /></p>
        </div>
      </div>

      <div className="po-layout">
        <section className="sheet sheet--canary panel">
          <h2 className="label">Lines · ordered / received / invoiced</h2>
          <ul className="fulfil">
            {po.lines.map((l) => {
              const max = Math.max(l.quantity, l.received_qty, l.invoiced_qty ?? 0, 1);
              return (
                <li key={l.po_line_id}>
                  <div className="fulfil__head">
                    <span className="num muted">{l.line_num}</span>
                    <span>{l.description} <span className="num muted">· {l.item_number}</span></span>
                    <span className="num">{qty(l.quantity)} {l.uom} @ {money(l.unit_price)}</span>
                  </div>
                  <div className="fulfil__bars" aria-label={`Ordered ${l.quantity}, received ${l.received_qty}, invoiced ${l.invoiced_qty ?? 0}`}>
                    <span className="fbar fbar--ordered" style={{ width: `${(l.quantity / max) * 100}%` }}><em>ordered {qty(l.quantity)}</em></span>
                    <span className="fbar fbar--received" style={{ width: `${(l.received_qty / max) * 100}%` }}><em>received {qty(l.received_qty)}</em></span>
                    <span className="fbar fbar--invoiced" style={{ width: `${((l.invoiced_qty ?? 0) / max) * 100}%` }}><em>invoiced {qty(l.invoiced_qty ?? 0)}</em></span>
                  </div>
                </li>
              );
            })}
          </ul>
          <p className="muted small">Outline: ordered · solid: received · hatched: invoiced through ProcureAI.</p>
        </section>

        <div className="po-side">
          <section className="sheet sheet--pink panel">
            <h2 className="label">Goods receipt</h2>
            {grn ? (
              <>
                <p className="num">{grn.grn_number}</p>
                <p className="muted">{grn.lines_received} of {grn.lines_total} lines received · last {date(grn.received_date)}</p>
              </>
            ) : <p className="muted">Nothing received yet.</p>}
          </section>
          <section className="sheet panel">
            <h2 className="label">Invoices against this PO</h2>
            {invoices.length === 0 ? <p className="muted">None yet.</p> : (
              <ol className="ruled-list">
                {invoices.map((i) => (
                  <li key={i.id}>
                    <Link href={`/app/invoices/${i.id}`} className="num">{i.invoice_number ?? i.original_filename}</Link>
                    <StatusInk status={i.status} />
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
