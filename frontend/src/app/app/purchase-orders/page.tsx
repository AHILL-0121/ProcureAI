'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { EmptyTray, Hl, LedgerSkeleton, Money, Notice } from '@/components/ui';
import { get, qs } from '@/lib/api';
import { date } from '@/lib/format';
import { useDebounced } from '@/lib/hooks';
import type { POSummary } from '@/lib/types';

const PAGE_SIZE = 25;
const SORTS = [
  { key: '-order_date', label: 'Newest first' },
  { key: 'order_date', label: 'Oldest first' },
  { key: 'po_number', label: 'PO number' },
  { key: '-total', label: 'Largest value' },
];

export default function PurchaseOrdersPage() {
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('-order_date');
  const [page, setPage] = useState(1);
  const term = useDebounced(search.trim(), 300);
  const q = useQuery({
    queryKey: ['pos', term, sort, page],
    queryFn: () => get<{ items: POSummary[]; total: number }>(`/purchase-orders${qs({ q: term, sort, page, page_size: PAGE_SIZE })}`),
    placeholderData: keepPreviousData,
  });
  const total = q.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="screen">
      <div className="screen__head">
        <div>
          <p className="label">From the ERP</p>
          <h1 className="display screen__title">Purchase orders <span className="screen__count num">{total}</span></h1>
        </div>
        <div className="filters">
          <label className="sr-only" htmlFor="po-search">Search purchase orders</label>
          <input id="po-search" className="input" type="search" placeholder="PO number or vendor" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
          <label className="sr-only" htmlFor="po-sort">Sort</label>
          <select id="po-sort" className="input" value={sort} onChange={(e) => setSort(e.target.value)}>
            {SORTS.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
        </div>
      </div>
      <div className="sheet sheet--flush sheet--canary-edge">
        <div className="ledger" role="table" aria-label="Purchase orders">
          <div className="ledger__head po-grid" role="row">
            <span role="columnheader" className="label">PO</span>
            <span role="columnheader" className="label col-vendor">Vendor</span>
            <span role="columnheader" className="label col-age">Ordered</span>
            <span role="columnheader" className="label ta-r">Value</span>
            <span role="columnheader" className="label ta-r col-po">Lines</span>
            <span role="columnheader" className="label">Status</span>
          </div>
          {q.isLoading && <LedgerSkeleton />}
          {q.isError && <div className="pad"><Notice tone="bad">{(q.error as Error).message}</Notice></div>}
          {q.isSuccess && q.data.items.length === 0 && <EmptyTray title="No purchase orders found." />}
          {q.data?.items.map((p) => (
            <div key={p.po_number} role="row" tabIndex={0} className="row po-grid" onClick={() => router.push(`/app/purchase-orders/${p.po_number}`)} onKeyDown={(e) => e.key === 'Enter' && router.push(`/app/purchase-orders/${p.po_number}`)}>
              <span role="cell"><Link href={`/app/purchase-orders/${p.po_number}`} className="num inv-link" onClick={(e) => e.stopPropagation()}><Hl>{p.po_number}</Hl></Link></span>
              <span role="cell" className="col-vendor ellipsis">{p.vendor_name}</span>
              <span role="cell" className="col-age num muted">{date(p.order_date)}</span>
              <span role="cell" className="ta-r"><Money amount={p.total_amount} currency={p.currency} /></span>
              <span role="cell" className="ta-r col-po num">{p.line_count}</span>
              <span role="cell"><span className={`ink ink--${p.status === 'OPEN' ? 'info' : 'pencil'}`}>{p.status.toLowerCase()}</span></span>
            </div>
          ))}
          {pages > 1 && (
            <div className="pager">
              <button type="button" className="key key--plain key--sm" disabled={page <= 1} onClick={() => setPage((n) => n - 1)}>Previous</button>
              <span className="num muted">Page {page} of {pages}</span>
              <button type="button" className="key key--plain key--sm" disabled={page >= pages} onClick={() => setPage((n) => n + 1)}>Next</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
