'use client';

import { useEffect, useState } from 'react';
import { apiFetch, formatCurrency, getMatchColor, cn } from '@/lib/utils';
import { useWebSocket } from '@/components/WebSocketProvider';
import { MatchesPageSkeleton } from '@/components/Skeletons';
import type { MatchDetail } from '@/lib/types';

export default function MatchesPage() {
  const [matches, setMatches] = useState<MatchDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('');
  const [selected, setSelected] = useState<MatchDetail | null>(null);
  const { lastMessage } = useWebSocket();

  const fetchMatches = async () => {
    try {
      const params = filter ? `?result=${filter}` : '';
      const data = await apiFetch<{ matches: MatchDetail[]; total: number }>(`/matches${params}`);
      setMatches(data.matches);
    } catch (err) {
      console.error('Failed to fetch matches:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchMatches(); }, [filter]);
  useEffect(() => {
    if (lastMessage?.event === 'match_complete') fetchMatches();
  }, [lastMessage]);

  const resultOptions = ['', 'FULL_MATCH', 'PARTIAL_MATCH', 'NO_MATCH'];

  if (loading) return <MatchesPageSkeleton />;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="animate-fade-in-down">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-surface-900 to-surface-600 bg-clip-text text-transparent">Three-Way Matches</h1>
        <p className="text-sm text-surface-400">Invoice {'<->'} Purchase Order {'<->'} Goods Receipt reconciliation</p>
      </div>

      {/* Filter */}
      <div className="flex gap-2 animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
        {resultOptions.map((opt) => (
          <button
            key={opt || 'all'}
            onClick={() => setFilter(opt)}
            className={cn(
              'px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300',
              filter === opt
                ? 'btn-primary text-white shadow-lg shadow-primary-500/25'
                : 'glass text-surface-600 hover:bg-white/60 hover:shadow-md'
            )}
          >
            {opt ? opt.replace('_', ' ') : 'All'}
          </button>
        ))}
      </div>

      {/* Cards */}
      {matches.length === 0 ? (
        <div className="glass-card p-12 text-center animate-fade-in-up">
          <div className="text-4xl mb-3 animate-bounce-gentle">🔗</div>
          <p className="text-surface-400">No match results yet. Process invoices to see matches.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 stagger-children">
          {matches.map((match) => (
            <div
              key={match.invoice_id}
              onClick={() => setSelected(match)}
              className="glass-card p-5 cursor-pointer group"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-surface-800 group-hover:text-primary-700 transition-colors">{match.invoice_number || 'Unknown Invoice'}</p>
                  <p className="text-sm text-surface-400">{match.vendor_name || '-'}</p>
                </div>
                <span className={cn('px-3 py-1.5 rounded-full text-xs font-medium border backdrop-blur-sm', getMatchColor(match.match_result))}>
                  {match.match_result.replace('_', ' ')}
                </span>
              </div>

              <div className="mt-3 flex items-center gap-4 text-xs text-surface-400">
                <span>PO: <span className="font-mono text-surface-500">{match.po_reference || 'N/A'}</span></span>
                <span>Amount: <span className="font-medium text-surface-700">{formatCurrency(match.total_amount)}</span></span>
                {match.discrepancies && (
                  <span className="text-red-500 font-medium">
                    {match.discrepancies.length} discrepanc{match.discrepancies.length === 1 ? 'y' : 'ies'}
                  </span>
                )}
              </div>

              {/* Quick discrepancy preview */}
              {match.discrepancies && match.discrepancies.length > 0 && (
                <div className="mt-3 pt-3 border-t border-white/20">
                  {match.discrepancies.slice(0, 2).map((d, i) => (
                    <p key={i} className={cn(
                      'text-xs mt-1',
                      d.severity === 'HIGH' ? 'text-red-500' : 'text-amber-500'
                    )}>
                      ! {d.message}
                    </p>
                  ))}
                  {match.discrepancies.length > 2 && (
                    <p className="text-xs text-surface-400 mt-1">+{match.discrepancies.length - 2} more</p>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Match Detail Modal */}
      {selected && (
        <MatchDetailModal match={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  );
}

function MatchDetailModal({ match, onClose }: { match: MatchDetail; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm animate-fade-in" onClick={onClose}>
      <div
        className="glass-modal rounded-2xl max-w-3xl w-full mx-4 max-h-[85vh] overflow-y-auto animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/20">
          <h2 className="text-lg font-bold bg-gradient-to-r from-surface-900 to-surface-600 bg-clip-text text-transparent">Match Detail: {match.invoice_number}</h2>
          <button onClick={onClose} className="text-surface-400 hover:text-surface-600 text-xl transition-colors hover:rotate-90 duration-300">&times;</button>
        </div>

        <div className="p-6 space-y-6">
          {/* Summary - three cards */}
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="p-4 rounded-xl bg-sky-50/80 border border-sky-200/60 backdrop-blur-sm">
              <p className="text-xs text-sky-600 font-medium">INVOICE</p>
              <p className="text-sm font-bold mt-1 text-surface-800">{match.invoice_number || '-'}</p>
              <p className="text-xs text-surface-500">{formatCurrency(match.total_amount)}</p>
            </div>
            <div className="p-4 rounded-xl bg-teal-50/80 border border-teal-200/60 backdrop-blur-sm">
              <p className="text-xs text-teal-600 font-medium">PURCHASE ORDER</p>
              <p className="text-sm font-bold mt-1 text-surface-800">{match.po_reference || 'N/A'}</p>
              <p className="text-xs text-surface-500">
                {match.po_data ? formatCurrency(match.po_data.total_amount) : '-'}
              </p>
            </div>
            <div className="p-4 rounded-xl bg-emerald-50/80 border border-emerald-200/60 backdrop-blur-sm">
              <p className="text-xs text-emerald-600 font-medium">GOODS RECEIPT</p>
              <p className="text-sm font-bold mt-1 text-surface-800">
                {match.grn_data ? match.grn_data.grn_number : 'Not Found'}
              </p>
              <p className="text-xs text-surface-500">
                {match.grn_data ? match.grn_data.status : '-'}
              </p>
            </div>
          </div>

          {/* Match Result */}
          <div className={cn(
            'p-4 rounded-xl border text-center backdrop-blur-sm',
            getMatchColor(match.match_result)
          )}>
            <p className="text-lg font-bold">{match.match_result.replace('_', ' ')}</p>
          </div>

          {/* PO Items */}
          {match.po_data?.items && (
            <div>
              <h3 className="text-sm font-semibold text-surface-700 mb-2">PO Line Items</h3>
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
                    {match.po_data.items.map((item: any, i: number) => (
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
          )}

          {/* Discrepancies */}
          {match.discrepancies && match.discrepancies.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-red-700 mb-2">
                Discrepancies ({match.discrepancies.length})
              </h3>
              <div className="space-y-2 stagger-children">
                {match.discrepancies.map((d, i) => (
                  <div key={i} className={cn(
                    'p-3 rounded-xl text-xs border backdrop-blur-sm',
                    d.severity === 'HIGH' ? 'bg-red-50/80 border-red-200/60 text-red-800' :
                    d.severity === 'MEDIUM' ? 'bg-amber-50/80 border-amber-200/60 text-amber-800' :
                    'bg-sky-50/80 border-sky-200/60 text-sky-800'
                  )}>
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        'px-1.5 py-0.5 rounded text-[10px] font-bold',
                        d.severity === 'HIGH' ? 'bg-red-200/80' : 'bg-amber-200/80'
                      )}>
                        {d.severity}
                      </span>
                      <span className="font-semibold">{d.type}</span>
                    </div>
                    <p className="mt-1">{d.message}</p>
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
