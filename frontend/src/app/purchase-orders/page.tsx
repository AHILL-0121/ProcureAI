'use client';

import { useEffect, useState } from 'react';
import { apiFetch, formatCurrency, cn } from '@/lib/utils';
import { POPageSkeleton } from '@/components/Skeletons';

interface POLineItem {
  item_code: string;
  description: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

interface PurchaseOrderSummary {
  po_number: string;
  vendor_name: string;
  vendor_id: string;
  order_date: string;
  total_amount: number;
  currency: string;
  status: string;
  line_count: number;
}

interface PurchaseOrderDetail {
  po_number: string;
  vendor_name: string;
  vendor_id: string;
  order_date: string;
  expected_delivery: string;
  total_amount: number;
  tax_amount: number;
  currency: string;
  status: string;
  items: POLineItem[];
}

export default function PurchaseOrdersPage() {
  const [pos, setPOs] = useState<PurchaseOrderSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<PurchaseOrderDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchPOs = async () => {
    try {
      const params = search ? `?vendor=${encodeURIComponent(search)}` : '';
      const data = await apiFetch<{ purchase_orders: PurchaseOrderSummary[]; total: number }>(
        `/purchase-orders${params}`
      );
      setPOs(data.purchase_orders);
    } catch (err) {
      console.error('Failed to fetch POs:', err);
    } finally {
      setLoading(false);
    }
  };

  const selectPO = async (po: PurchaseOrderSummary) => {
    setDetailLoading(true);
    try {
      const data = await apiFetch<{ purchase_order: PurchaseOrderDetail }>(
        `/purchase-orders/${po.po_number}`
      );
      setSelected(data.purchase_order);
    } catch (err) {
      console.error('Failed to fetch PO details:', err);
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => { fetchPOs(); }, [search]);

  if (loading) return <POPageSkeleton />;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="animate-fade-in-down">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-surface-900 to-surface-600 bg-clip-text text-transparent">Purchase Orders</h1>
        <p className="text-sm text-surface-400">Oracle ERP Dataset &mdash; {pos.length} POs loaded</p>
      </div>

      {/* Search */}
      <div className="animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
        <input
          type="text"
          placeholder="Search by vendor name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="glass-input px-4 py-2.5 rounded-xl text-sm w-full max-w-md outline-none"
        />
      </div>

      {/* Table */}
      <div className="glass-table animate-fade-in-up" style={{ animationDelay: '0.15s' }}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-primary-500/10 bg-primary-500/5">
                <th className="text-left px-4 py-3 font-medium text-surface-500 text-xs uppercase tracking-wider">PO Number</th>
                <th className="text-left px-4 py-3 font-medium text-surface-500 text-xs uppercase tracking-wider">Vendor</th>
                <th className="text-left px-4 py-3 font-medium text-surface-500 text-xs uppercase tracking-wider">Order Date</th>
                <th className="text-right px-4 py-3 font-medium text-surface-500 text-xs uppercase tracking-wider">Amount</th>
                <th className="text-center px-4 py-3 font-medium text-surface-500 text-xs uppercase tracking-wider">Status</th>
                <th className="text-center px-4 py-3 font-medium text-surface-500 text-xs uppercase tracking-wider">Items</th>
              </tr>
            </thead>
            <tbody className="stagger-children">
              {pos.map((po) => (
                <tr
                  key={po.po_number}
                  onClick={() => selectPO(po)}
                  className="border-b border-white/10 hover:bg-primary-500/5 cursor-pointer transition-all duration-200 group"
                >
                  <td className="px-4 py-3.5 font-mono text-sm font-medium text-primary-700 group-hover:text-primary-600 transition-colors">{po.po_number}</td>
                  <td className="px-4 py-3.5 text-surface-700">{po.vendor_name}</td>
                  <td className="px-4 py-3.5 text-surface-400 text-xs">{po.order_date}</td>
                  <td className="px-4 py-3.5 text-right font-medium text-surface-800">{formatCurrency(po.total_amount)}</td>
                  <td className="px-4 py-3.5 text-center">
                    <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100/80 text-emerald-700 backdrop-blur-sm">
                      {po.status}
                    </span>
                  </td>
                  <td className="px-4 py-3.5 text-center text-surface-500">{po.line_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail Modal */}
      {selected && (
        <PODetailModal po={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function PODetailModal({ po, onClose }: { po: PurchaseOrderDetail; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm animate-fade-in" onClick={onClose}>
      <div
        className="glass-modal rounded-2xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/20">
          <h2 className="text-lg font-bold bg-gradient-to-r from-surface-900 to-surface-600 bg-clip-text text-transparent">{po.po_number}</h2>
          <button onClick={onClose} className="text-surface-400 hover:text-surface-600 text-xl transition-colors hover:rotate-90 duration-300">&times;</button>
        </div>

        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div><span className="text-surface-400">Vendor:</span> <span className="ml-1 font-medium text-surface-800">{po.vendor_name}</span></div>
            <div><span className="text-surface-400">Vendor ID:</span> <span className="ml-1 font-mono text-surface-600">{po.vendor_id}</span></div>
            <div><span className="text-surface-400">Order Date:</span> <span className="ml-1 text-surface-700">{po.order_date}</span></div>
            <div><span className="text-surface-400">Delivery:</span> <span className="ml-1 text-surface-700">{po.expected_delivery}</span></div>
            <div><span className="text-surface-400">Total:</span> <span className="ml-1 font-bold text-surface-800">{formatCurrency(po.total_amount)}</span></div>
            <div><span className="text-surface-400">Tax:</span> <span className="ml-1 text-surface-700">{formatCurrency(po.tax_amount)}</span></div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-surface-700 mb-2">Line Items</h3>
            <div className="glass rounded-xl overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-primary-500/10 bg-primary-500/5">
                    <th className="text-left px-3 py-2">Code</th>
                    <th className="text-left px-3 py-2">Description</th>
                    <th className="text-right px-3 py-2">Qty</th>
                    <th className="text-right px-3 py-2">Unit Price</th>
                    <th className="text-right px-3 py-2">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {(po.items || []).map((item, i) => (
                    <tr key={i} className="border-b border-white/10">
                      <td className="px-3 py-2 font-mono text-surface-600">{item.item_code}</td>
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
        </div>
      </div>
    </div>
  );
}
