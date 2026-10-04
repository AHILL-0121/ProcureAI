'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Blot, EmptyTray, Hl, LedgerSkeleton, Money, Notice, StatusInk } from '@/components/ui';
import { get, qs } from '@/lib/api';
import { date } from '@/lib/format';
import { useDebounced } from '@/lib/hooks';
import type { InvoiceSummary, Page } from '@/lib/types';

const QUEUES = [
  { key: '', label: 'All' },
  { key: 'review', label: 'Waiting' },
  { key: 'processing', label: 'Being read' },
  { key: 'cleared', label: 'Cleared' },
  { key: 'failed', label: 'Failed & duplicates' },
];
const SORTS = [
  { key: '-created_at', label: 'Newest' },
  { key: 'created_at', label: 'Oldest' },
  { key: '-amount', label: 'Largest amount' },
  { key: 'vendor', label: 'Vendor A–Z' },
];
const PAGE_SIZE = 25;

export default function InvoicesPage() {
  const router = useRouter();
  const [queue, setQueue] = useState('');
  const [sort, setSort] = useState('-created_at');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const term = useDebounced(search.trim(), 300);

  const q = useQuery({
    queryKey: ['invoices', 'list', queue, sort, term, page],
    queryFn: () => get<Page<InvoiceSummary>>(`/invoices${qs({ queue, sort, search: term, page, page_size: PAGE_SIZE })}`),
    placeholderData: keepPreviousData,
  });
  const total = q.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="screen">
      <div className="screen__head">
        <div>
          <p className="label">Every invoice received</p>
          <h1 className="display screen__title">Invoices <span className="screen__count num">{total}</span></h1>
        </div>
        <div className="filters">
          <label className="sr-only" htmlFor="inv-search">Search invoices</label>
          <input id="inv-search" className="input" type="search" placeholder="Number, vendor, PO or file name" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
          <label className="sr-only" htmlFor="inv-sort">Sort</label>
          <select id="inv-sort" className="input" value={sort} onChange={(e) => setSort(e.target.value)}>
            {SORTS.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
        </div>
      </div>

      <div className="sheet sheet--flush">
        <div className="ptabs" role="group" aria-label="Filter by state">
          {QUEUES.map((t) => (
            <button key={t.key || 'all'} type="button" className="ptab" aria-pressed={queue === t.key} onClick={() => { setQueue(t.key); setPage(1); }}>{t.label}</button>
          ))}
        </div>
        <div className="ledger" role="table" aria-label="Invoices">
          <div className="ledger__head inv-grid" role="row">
            <span role="columnheader"><span className="sr-only">Severity</span></span>
            <span role="columnheader" className="label">Invoice</span>
            <span role="columnheader" className="label col-vendor">Vendor</span>
            <span role="columnheader" className="label col-po">PO</span>
            <span role="columnheader" className="label ta-r">Amount</span>
            <span role="columnheader" className="label">State</span>
            <span role="columnheader" className="label ta-r col-age">Received</span>
          </div>
          {q.isLoading && <LedgerSkeleton />}
          {q.isError && <div className="pad"><Notice tone="bad">{(q.error as Error).message}</Notice></div>}
          {q.isSuccess && q.data.items.length === 0 && <EmptyTray title="No invoices here.">{term ? 'Nothing matches that search.' : 'Add invoices with the button above, or drop them anywhere.'}</EmptyTray>}
          {q.data?.items.map((r) => (
            <div key={r.id} role="row" tabIndex={0} className="row inv-grid" onClick={() => router.push(`/app/invoices/${r.id}`)} onKeyDown={(e) => e.key === 'Enter' && router.push(`/app/invoices/${r.id}`)}>
              <span role="cell"><Blot severity={r.top_issue_severity} /></span>
              <span role="cell" className="cell-inv">
                <Link href={`/app/invoices/${r.id}`} className="num inv-link" onClick={(e) => e.stopPropagation()}><Hl>{r.invoice_number || r.original_filename || 'Unread'}</Hl></Link>
                <small className="muted mobile-only">{r.vendor_name}</small>
              </span>
              <span role="cell" className="col-vendor ellipsis">{r.vendor_name || '—'}</span>
              <span role="cell" className="col-po num muted">{r.po_reference || '—'}</span>
              <span role="cell" className="ta-r"><Money amount={r.total_amount} currency={r.currency} /></span>
              <span role="cell"><StatusInk status={r.status} /></span>
              <span role="cell" className="ta-r col-age num muted">{date(r.created_at, { day: '2-digit', month: 'short' })}</span>
            </div>
          ))}
          {pages > 1 && (
            <div className="pager">
              <button type="button" className="key key--plain key--sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</button>
              <span className="num muted">Page {page} of {pages}</span>
              <button type="button" className="key key--plain key--sm" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
