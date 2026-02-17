'use client';

import { useEffect, useState } from 'react';
import { apiFetch, formatCurrency, formatDate, getStatusColor, getMatchColor, cn } from '@/lib/utils';
import { useWebSocket } from '@/components/WebSocketProvider';
import { InvoicesPageSkeleton } from '@/components/Skeletons';
import type { Invoice } from '@/lib/types';

export default function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<Invoice | null>(null);
  const { lastMessage } = useWebSocket();

  const fetchInvoices = async () => {
    try {
      const params = new URLSearchParams();
      if (filter) params.set('status', filter);
      if (search) params.set('search', search);
      const data = await apiFetch<{ invoices: Invoice[]; total: number }>(
        `/invoices?${params.toString()}`
      );
      setInvoices(data.invoices);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to fetch invoices:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchInvoices(); }, [filter, search]);
  useEffect(() => {
    if (lastMessage?.event === 'match_complete' || lastMessage?.event === 'status_update') {
      fetchInvoices();
    }
  }, [lastMessage]);

  const statusOptions = ['', 'RECEIVED', 'EXTRACTING', 'EXTRACTED', 'VALIDATED', 'MATCHED', 'DISCREPANCY', 'FAILED'];

  if (loading) return <InvoicesPageSkeleton />;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between animate-fade-in-down">
        <div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-surface-900 to-surface-600 bg-clip-text text-transparent">
            Invoices
          </h1>
          <p className="text-sm text-surface-400">{total} invoice{total !== 1 ? 's' : ''} processed</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
        <input
          type="text"
          placeholder="Search by invoice #, vendor, PO..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="glass-input px-4 py-2.5 rounded-xl text-sm flex-1 min-w-[200px] outline-none"
        />
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="glass-input px-4 py-2.5 rounded-xl text-sm outline-none cursor-pointer"
        >
          <option value="">All Statuses</option>
          {statusOptions.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      {invoices.length === 0 ? (
        <div className="glass-card p-12 text-center animate-fade-in-up">
          <div className="text-4xl mb-3 animate-bounce-gentle">📄</div>
          <p className="text-surface-400 text-sm">No invoices found. Upload one to get started!</p>
        </div>
      ) : (
        <div className="glass-table animate-fade-in-up" style={{ animationDelay: '0.15s' }}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-primary-500/10 bg-primary-500/5">
                  <th className="text-left px-4 py-3 font-medium text-surface-500 text-xs uppercase tracking-wider">Invoice #</th>
                  <th className="text-left px-4 py-3 font-medium text-surface-500 text-xs uppercase tracking-wider">Vendor</th>
                  <th className="text-left px-4 py-3 font-medium text-surface-500 text-xs uppercase tracking-wider">PO Ref</th>
                  <th className="text-right px-4 py-3 font-medium text-surface-500 text-xs uppercase tracking-wider">Amount</th>
                  <th className="text-center px-4 py-3 font-medium text-surface-500 text-xs uppercase tracking-wider">Status</th>
                  <th className="text-center px-4 py-3 font-medium text-surface-500 text-xs uppercase tracking-wider">Match</th>
                  <th className="text-right px-4 py-3 font-medium text-surface-500 text-xs uppercase tracking-wider">Time</th>
                  <th className="text-right px-4 py-3 font-medium text-surface-500 text-xs uppercase tracking-wider">Date</th>
                </tr>
              </thead>
              <tbody className="stagger-children">
                {invoices.map((inv) => (
                  <tr
                    key={inv.id}
                    onClick={() => setSelected(inv)}
                    className="border-b border-white/10 hover:bg-primary-500/5 cursor-pointer transition-all duration-200 group"
                  >
                    <td className="px-4 py-3.5 font-medium text-surface-800 group-hover:text-primary-700 transition-colors">{inv.invoice_number || '-'}</td>
                    <td className="px-4 py-3.5 text-surface-600">{inv.vendor_name || '-'}</td>
                    <td className="px-4 py-3.5 text-surface-500 font-mono text-xs">{inv.po_reference || '-'}</td>
                    <td className="px-4 py-3.5 text-right font-medium text-surface-800">{formatCurrency(inv.total_amount)}</td>
                    <td className="px-4 py-3.5 text-center">
                      <span className={cn('px-2.5 py-1 rounded-full text-xs font-medium backdrop-blur-sm', getStatusColor(inv.status))}>
                        {inv.status}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-center">
                      <span className={cn('px-2.5 py-1 rounded-full text-xs font-medium border backdrop-blur-sm', getMatchColor(inv.match_result))}>
                        {inv.match_result}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 text-right text-surface-400 text-xs">
                      {inv.processing_time ? `${inv.processing_time}s` : '-'}
                    </td>
                    <td className="px-4 py-3.5 text-right text-surface-400 text-xs">{formatDate(inv.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Detail Modal */}
      {selected && (
        <InvoiceDetailModal invoice={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function InvoiceDetailModal({ invoice, onClose }: { invoice: Invoice; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm animate-fade-in" onClick={onClose}>
      <div
        className="glass-modal rounded-2xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/20">
          <h2 className="text-lg font-bold bg-gradient-to-r from-surface-900 to-surface-600 bg-clip-text text-transparent">
            Invoice Detail
          </h2>
          <button onClick={onClose} className="text-surface-400 hover:text-surface-600 text-xl transition-colors hover:rotate-90 duration-300">
            &times;
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* Header info */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-surface-400">Invoice #:</span>
              <span className="ml-2 font-medium text-surface-800">{invoice.invoice_number || '-'}</span>
            </div>
            <div>
              <span className="text-surface-400">Vendor:</span>
              <span className="ml-2 font-medium text-surface-800">{invoice.vendor_name || '-'}</span>
            </div>
            <div>
              <span className="text-surface-400">PO Reference:</span>
              <span className="ml-2 font-mono text-xs text-surface-600">{invoice.po_reference || '-'}</span>
            </div>
            <div>
              <span className="text-surface-400">Total:</span>
              <span className="ml-2 font-bold text-surface-800">{formatCurrency(invoice.total_amount)}</span>
            </div>
            <div>
              <span className="text-surface-400">Date:</span>
              <span className="ml-2 text-surface-700">{invoice.invoice_date || '-'}</span>
            </div>
            <div>
              <span className="text-surface-400">Confidence:</span>
              <span className="ml-2 text-surface-700">{(invoice.confidence_score * 100).toFixed(0)}%</span>
            </div>
          </div>

          {/* Status badges */}
          <div className="flex gap-2 flex-wrap">
            <span className={cn('px-3 py-1.5 rounded-full text-xs font-medium backdrop-blur-sm', getStatusColor(invoice.status))}>
              {invoice.status}
            </span>
            <span className={cn('px-3 py-1.5 rounded-full text-xs font-medium border backdrop-blur-sm', getMatchColor(invoice.match_result))}>
              {invoice.match_result}
            </span>
            <span className="px-3 py-1.5 rounded-full text-xs font-medium bg-surface-100/80 text-surface-600 backdrop-blur-sm">
              {invoice.invoice_type}
            </span>
          </div>

          {/* Line Items */}
          {invoice.line_items && invoice.line_items.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-surface-700 mb-2">Line Items</h3>
              <div className="glass rounded-xl overflow-hidden">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-primary-500/10 bg-primary-500/5">
                      <th className="text-left px-3 py-2">Code</th>
                      <th className="text-left px-3 py-2">Description</th>
                      <th className="text-right px-3 py-2">Qty</th>
                      <th className="text-right px-3 py-2">Price</th>
                      <th className="text-right px-3 py-2">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoice.line_items.map((item, i) => (
                      <tr key={i} className="border-b border-white/10">
                        <td className="px-3 py-2 font-mono text-surface-600">{item.item_code || '-'}</td>
                        <td className="px-3 py-2 text-surface-700">{item.description}</td>
                        <td className="px-3 py-2 text-right text-surface-600">{item.quantity}</td>
                        <td className="px-3 py-2 text-right text-surface-600">{formatCurrency(item.unit_price)}</td>
                        <td className="px-3 py-2 text-right font-medium text-surface-800">{formatCurrency(item.total_price)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Discrepancies */}
          {invoice.discrepancies && invoice.discrepancies.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-red-700 mb-2">Discrepancies ({invoice.discrepancies.length})</h3>
              <div className="space-y-2 stagger-children">
                {invoice.discrepancies.map((d, i) => (
                  <div key={i} className={cn(
                    'p-3 rounded-xl text-xs border backdrop-blur-sm',
                    d.severity === 'HIGH' ? 'bg-red-50/80 border-red-200/60 text-red-800' :
                    d.severity === 'MEDIUM' ? 'bg-amber-50/80 border-amber-200/60 text-amber-800' :
                    'bg-sky-50/80 border-sky-200/60 text-sky-800'
                  )}>
                    <span className="font-semibold">[{d.severity}] {d.type}:</span> {d.message}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
