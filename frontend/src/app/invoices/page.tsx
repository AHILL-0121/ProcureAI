'use client';

import { useEffect, useState } from 'react';
import { apiFetch, formatCurrency, formatDate, getStatusColor, getMatchColor, cn } from '@/lib/utils';
import { useWebSocket } from '@/components/WebSocketProvider';
import { InvoicesPageSkeleton } from '@/components/Skeletons';
import type { Invoice } from '@/lib/types';
import { tokens } from '@/lib/design-tokens';
import { Badge } from '@/components/UIComponents';

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
          <h1 className="text-2xl font-bold" style={{
            background: `linear-gradient(to right, ${tokens.charcoal}, ${tokens.slate})`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text'
          }}>
            Invoices
          </h1>
          <p className="text-sm" style={{ color: tokens.mist }}>{total} invoice{total !== 1 ? 's' : ''} processed</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
        <input
          type="text"
          placeholder="Search by invoice #, vendor, PO..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="warm-input px-4 py-2.5 flex-1 min-w-[200px]"
        />
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="warm-input px-4 py-2.5 cursor-pointer"
        >
          <option value="">All Statuses</option>
          {statusOptions.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      {invoices.length === 0 ? (
        <div className="warm-card p-12 text-center animate-fade-in-up">
          <div className="text-4xl mb-3">📄</div>
          <p className="text-sm" style={{ color: tokens.mist }}>No invoices found. Upload one to get started!</p>
        </div>
      ) : (
        <div className="warm-card overflow-hidden animate-fade-in-up" style={{ animationDelay: '0.15s' }}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: `1px solid ${tokens.sand}80`, background: `${tokens.parchment}` }}>
                  <th className="text-left px-4 py-3 font-medium text-xs uppercase tracking-wider" style={{ color: tokens.slate }}>Invoice #</th>
                  <th className="text-left px-4 py-3 font-medium text-xs uppercase tracking-wider" style={{ color: tokens.slate }}>Vendor</th>
                  <th className="text-left px-4 py-3 font-medium text-xs uppercase tracking-wider" style={{ color: tokens.slate }}>PO Ref</th>
                  <th className="text-right px-4 py-3 font-medium text-xs uppercase tracking-wider" style={{ color: tokens.slate }}>Amount</th>
                  <th className="text-center px-4 py-3 font-medium text-xs uppercase tracking-wider" style={{ color: tokens.slate }}>Status</th>
                  <th className="text-center px-4 py-3 font-medium text-xs uppercase tracking-wider" style={{ color: tokens.slate }}>Match</th>
                  <th className="text-right px-4 py-3 font-medium text-xs uppercase tracking-wider" style={{ color: tokens.slate }}>Time</th>
                  <th className="text-right px-4 py-3 font-medium text-xs uppercase tracking-wider" style={{ color: tokens.slate }}>Date</th>
                </tr>
              </thead>
              <tbody className="stagger-children">
                {invoices.map((inv) => (
                  <tr
                    key={inv.id}
                    onClick={() => setSelected(inv)}
                    className="cursor-pointer transition-all duration-200 group"
                    style={{ borderBottom: `1px solid ${tokens.sand}40` }}
                    onMouseEnter={(e) => e.currentTarget.style.background = `${tokens.amber}08`}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <td className="px-4 py-3.5 font-medium transition-colors" style={{ color: tokens.charcoal }}>{inv.invoice_number || '-'}</td>
                    <td className="px-4 py-3.5" style={{ color: tokens.slate }}>{inv.vendor_name || '-'}</td>
                    <td className="px-4 py-3.5 font-mono text-xs" style={{ color: tokens.mist }}>{inv.po_reference || '-'}</td>
                    <td className="px-4 py-3.5 text-right font-medium" style={{ color: tokens.charcoal }}>{formatCurrency(inv.total_amount)}</td>
                    <td className="px-4 py-3.5 text-center">
                      <Badge type={inv.status} />
                    </td>
                    <td className="px-4 py-3.5 text-center">
                      <Badge type={inv.match_result || 'PROCESSING'} />
                    </td>
                    <td className="px-4 py-3.5 text-right text-xs" style={{ color: tokens.mist }}>
                      {inv.processing_time ? `${inv.processing_time}s` : '-'}
                    </td>
                    <td className="px-4 py-3.5 text-right text-xs" style={{ color: tokens.mist }}>{formatDate(inv.created_at)}</td>
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
    <div className="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm animate-fade-in" 
      style={{ background: 'rgba(0,0,0,0.3)' }} onClick={onClose}>
      <div
        className="warm-card rounded-2xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto"
        style={{ animation: 'slideUp 0.35s cubic-bezier(0.16,1,0.3,1)' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: `${tokens.sand}80` }}>
          <h2 className="text-lg font-bold" style={{
            background: `linear-gradient(to right, ${tokens.charcoal}, ${tokens.slate})`,
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text'
          }}>
            Invoice Detail
          </h2>
          <button onClick={onClose} className="text-xl transition-all duration-300" 
            style={{ color: tokens.mist }}
            onMouseEnter={(e) => { e.currentTarget.style.color = tokens.ember; e.currentTarget.style.transform = 'rotate(90deg)'; }}
            onMouseLeave={(e) => { e.currentTarget.style.color = tokens.mist; e.currentTarget.style.transform = 'rotate(0deg)'; }}
          >
            &times;
          </button>
        </div>

        <div className="p-6 space-y-4">
          {/* Header info */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span style={{ color: tokens.mist }}>Invoice #:</span>
              <span className="ml-2 font-medium" style={{ color: tokens.charcoal }}>{invoice.invoice_number || '-'}</span>
            </div>
            <div>
              <span style={{ color: tokens.mist }}>Vendor:</span>
              <span className="ml-2 font-medium" style={{ color: tokens.charcoal }}>{invoice.vendor_name || '-'}</span>
            </div>
            <div>
              <span style={{ color: tokens.mist }}>PO Reference:</span>
              <span className="ml-2 font-mono text-xs" style={{ color: tokens.slate }}>{invoice.po_reference || '-'}</span>
            </div>
            <div>
              <span style={{ color: tokens.mist }}>Total:</span>
              <span className="ml-2 font-bold" style={{ color: tokens.charcoal }}>{formatCurrency(invoice.total_amount)}</span>
            </div>
            <div>
              <span style={{ color: tokens.mist }}>Date:</span>
              <span className="ml-2" style={{ color: tokens.slate }}>{invoice.invoice_date || '-'}</span>
            </div>
            <div>
              <span style={{ color: tokens.mist }}>Confidence:</span>
              <span className="ml-2" style={{ color: tokens.slate }}>{(invoice.confidence_score * 100).toFixed(0)}%</span>
            </div>
          </div>

          {/* Status badges */}
          <div className="flex gap-2 flex-wrap">
            <Badge type={invoice.status} />
            <Badge type={invoice.match_result || 'PROCESSING'} />
            <span className="px-3 py-1.5 rounded-full text-xs font-medium" style={{
              background: `${tokens.sand}80`,
              color: tokens.slate
            }}>
              {invoice.invoice_type}
            </span>
          </div>

          {/* Line Items */}
          {invoice.line_items && invoice.line_items.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold mb-2" style={{ color: tokens.charcoal }}>Line Items</h3>
              <div className="rounded-xl overflow-hidden" style={{ border: `1px solid ${tokens.sand}` }}>
                <table className="w-full text-xs">
                  <thead>
                    <tr style={{ borderBottom: `1px solid ${tokens.sand}80`, background: tokens.parchment }}>
                      <th className="text-left px-3 py-2" style={{ color: tokens.slate }}>Code</th>
                      <th className="text-left px-3 py-2" style={{ color: tokens.slate }}>Description</th>
                      <th className="text-right px-3 py-2" style={{ color: tokens.slate }}>Qty</th>
                      <th className="text-right px-3 py-2" style={{ color: tokens.slate }}>Price</th>
                      <th className="text-right px-3 py-2" style={{ color: tokens.slate }}>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoice.line_items.map((item, i) => (
                      <tr key={i} style={{ borderBottom: `1px solid ${tokens.sand}40` }}>
                        <td className="px-3 py-2 font-mono" style={{ color: tokens.slate }}>{item.item_code || '-'}</td>
                        <td className="px-3 py-2" style={{ color: tokens.charcoal }}>{item.description}</td>
                        <td className="px-3 py-2 text-right" style={{ color: tokens.slate }}>{item.quantity}</td>
                        <td className="px-3 py-2 text-right" style={{ color: tokens.slate }}>{formatCurrency(item.unit_price)}</td>
                        <td className="px-3 py-2 text-right font-medium" style={{ color: tokens.charcoal }}>{formatCurrency(item.total_price)}</td>
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
              <h3 className="text-sm font-semibold mb-2" style={{ color: tokens.crimson }}>Discrepancies ({invoice.discrepancies.length})</h3>
              <div className="space-y-2 stagger-children">
                {invoice.discrepancies.map((d, i) => (
                  <div key={i} className="p-3 rounded-xl text-xs border" style={{
                    background: d.severity === 'HIGH' ? '#FEE2E2' : d.severity === 'MEDIUM' ? '#FEF9C3' : '#F0F9FF',
                    borderColor: d.severity === 'HIGH' ? tokens.crimson : d.severity === 'MEDIUM' ? tokens.gold : '#0284C7',
                    color: d.severity === 'HIGH' ? tokens.crimson : d.severity === 'MEDIUM' ? tokens.ember : '#0369A1'
                  }}>
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
