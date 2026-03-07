'use client';

import { useEffect, useState } from 'react';
import { apiFetch, formatCurrency, getMatchColor, cn } from '@/lib/utils';
import { useWebSocket } from '@/components/WebSocketProvider';
import { MatchesPageSkeleton } from '@/components/Skeletons';
import type { MatchDetail } from '@/lib/types';
import { tokens } from '@/lib/design-tokens';
import { Badge } from '@/components/UIComponents';

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
        <h1 className="text-2xl font-bold" style={{
          background: `linear-gradient(to right, ${tokens.charcoal}, ${tokens.slate})`,
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text'
        }}>Three-Way Matches</h1>
        <p className="text-sm" style={{ color: tokens.mist }}>Invoice {'<->'} Purchase Order {'<->'} Goods Receipt reconciliation</p>
      </div>

      {/* Filter */}
      <div className="flex gap-2 animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
        {resultOptions.map((opt) => (
          <button
            key={opt || 'all'}
            onClick={() => setFilter(opt)}
            className="px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300"
            style={{
              background: filter === opt 
                ? `linear-gradient(135deg, ${tokens.amber}, ${tokens.ember})` 
                : tokens.sand,
              color: filter === opt ? 'white' : tokens.slate,
              boxShadow: filter === opt ? `0 4px 14px ${tokens.amber}40` : 'none',
              border: filter === opt ? 'none' : `1px solid ${tokens.sand}`
            }}
          >
            {opt ? opt.replace('_', ' ') : 'All'}
          </button>
        ))}
      </div>

      {/* Cards */}
      {matches.length === 0 ? (
        <div className="warm-card p-12 text-center animate-fade-in-up">
          <div className="text-4xl mb-3">🔗</div>
          <p style={{ color: tokens.mist }}>No match results yet. Process invoices to see matches.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 stagger-children">
          {matches.map((match) => (
            <div
              key={match.invoice_id}
              onClick={() => setSelected(match)}
              className="warm-card p-5 cursor-pointer group"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold transition-colors" style={{ color: tokens.charcoal }}>{match.invoice_number || 'Unknown Invoice'}</p>
                  <p className="text-sm" style={{ color: tokens.mist }}>{match.vendor_name || '-'}</p>
                </div>
                <Badge type={match.match_result} />
              </div>

              <div className="mt-3 flex items-center gap-4 text-xs" style={{ color: tokens.mist }}>
                <span>PO: <span className="font-mono" style={{ color: tokens.slate }}>{match.po_reference || 'N/A'}</span></span>
                <span>Amount: <span className="font-medium" style={{ color: tokens.charcoal }}>{formatCurrency(match.total_amount)}</span></span>
                {match.discrepancies && (
                  <span className="font-medium" style={{ color: tokens.crimson }}>
                    {match.discrepancies.length} discrepanc{match.discrepancies.length === 1 ? 'y' : 'ies'}
                  </span>
                )}
              </div>

              {/* Quick discrepancy preview */}
              {match.discrepancies && match.discrepancies.length > 0 && (
                <div className="mt-3 pt-3" style={{ borderTop: `1px solid ${tokens.sand}80` }}>
                  {match.discrepancies.slice(0, 2).map((d, i) => (
                    <p key={i} className="text-xs mt-1" style={{
                      color: d.severity === 'HIGH' ? tokens.crimson : tokens.amber
                    }}>
                      ! {d.message}
                    </p>
                  ))}
                  {match.discrepancies.length > 2 && (
                    <p className="text-xs mt-1" style={{ color: tokens.mist }}>+{match.discrepancies.length - 2} more</p>
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
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in" 
      style={{ 
        backgroundColor: 'rgba(253, 250, 244, 0.7)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)'
      }}
      onClick={onClose}
    >
      <div
        className="warm-card max-w-4xl w-full max-h-[85vh] overflow-y-auto animate-slide-up shadow-2xl my-auto"
        onClick={(e) => e.stopPropagation()}
        style={{ position: 'relative' }}
      >
        <div className="sticky top-0 z-10 flex items-center justify-between px-4 sm:px-6 py-4" style={{ 
          background: 'white',
          borderBottom: `1.5px solid ${tokens.sand}`
        }}>
          <h2 className="text-base sm:text-lg font-bold truncate pr-4" style={{ color: tokens.charcoal }}>
            Match Detail: {match.invoice_number}
          </h2>
          <button 
            onClick={onClose} 
            className="text-2xl transition-all duration-300 hover:rotate-90 flex-shrink-0 hover:scale-110"
            style={{ color: tokens.mist }}
          >
            ×
          </button>
        </div>

        <div className="p-4 sm:p-6 space-y-4 sm:space-y-6">
          {/* Summary - three cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
            <div className="p-4 rounded-xl" style={{ 
              background: `${tokens.forest}10`,
              border: `1px solid ${tokens.forest}30`
            }}>
              <p className="text-xs font-medium" style={{ color: tokens.forest }}>INVOICE</p>
              <p className="text-sm font-bold mt-1 truncate" style={{ color: tokens.charcoal }}>{match.invoice_number || '-'}</p>
              <p className="text-xs truncate" style={{ color: tokens.mist }}>{formatCurrency(match.total_amount)}</p>
              {match.invoice_file_path && (
                <button
                  onClick={() => window.open(`http://localhost:8001/api/documents/invoice/${match.invoice_id}`, '_blank')}
                  className="mt-2 text-xs px-3 py-1.5 rounded-lg transition-all duration-200 hover:scale-105 w-full"
                  style={{ 
                    background: tokens.forest,
                    color: 'white',
                    fontWeight: 500
                  }}
                >
                  📄 View Document
                </button>
              )}
            </div>
            <div className="p-4 rounded-xl" style={{ 
              background: `${tokens.amber}10`,
              border: `1px solid ${tokens.amber}30`
            }}>
              <p className="text-xs font-medium" style={{ color: tokens.amber }}>PURCHASE ORDER</p>
              <p className="text-sm font-bold mt-1 truncate" style={{ color: tokens.charcoal }}>{match.po_reference || 'N/A'}</p>
              <p className="text-xs truncate" style={{ color: tokens.mist }}>
                {match.po_data ? formatCurrency(match.po_data.total_amount) : '-'}
              </p>
              {match.po_data && (
                <div
                  className="mt-2 text-xs px-3 py-1.5 rounded-lg text-center"
                  style={{ 
                    background: `${tokens.amber}20`,
                    color: tokens.amber,
                    fontWeight: 500
                  }}
                >
                  ERP System
                </div>
              )}
            </div>
            <div className="p-4 rounded-xl" style={{ 
              background: `${tokens.sage}10`,
              border: `1px solid ${tokens.sage}30`
            }}>
              <p className="text-xs font-medium" style={{ color: tokens.sage }}>GOODS RECEIPT</p>
              <p className="text-sm font-bold mt-1 truncate" style={{ color: tokens.charcoal }}>
                {match.grn_data ? match.grn_data.grn_number : 'Not Found'}
              </p>
              <p className="text-xs truncate" style={{ color: tokens.mist }}>
                {match.grn_data ? match.grn_data.status : '-'}
              </p>
              {match.grn_data && (
                <div
                  className="mt-2 text-xs px-3 py-1.5 rounded-lg text-center"
                  style={{ 
                    background: `${tokens.sage}20`,
                    color: tokens.sage,
                    fontWeight: 500
                  }}
                >
                  ERP System
                </div>
              )}
            </div>
          </div>

          {/* Match Result */}
          <div className="p-4 rounded-xl text-center" style={{
            background: match.match_result === 'FULL_MATCH' ? `${tokens.forest}20` : 
                       match.match_result === 'PARTIAL_MATCH' ? `${tokens.amber}20` : `${tokens.crimson}20`,
            border: `2px solid ${match.match_result === 'FULL_MATCH' ? tokens.forest : 
                                 match.match_result === 'PARTIAL_MATCH' ? tokens.amber : tokens.crimson}`
          }}>
            <p className="text-lg font-bold" style={{
              color: match.match_result === 'FULL_MATCH' ? tokens.forest : 
                     match.match_result === 'PARTIAL_MATCH' ? tokens.amber : tokens.crimson
            }}>
              {match.match_result.replace('_', ' ')}
            </p>
          </div>

          {/* PO Items */}
          {match.po_data?.items && (
            <div>
              <h3 className="text-sm font-semibold mb-2" style={{ color: tokens.charcoal }}>PO Line Items</h3>
              <div className="rounded-xl overflow-x-auto" style={{ 
                background: tokens.parchment,
                border: `1px solid ${tokens.sand}`
              }}>
                <table className="w-full text-xs min-w-[500px]">
                  <thead>
                    <tr style={{ 
                      borderBottom: `1px solid ${tokens.sand}`,
                      background: tokens.sand
                    }}>
                      <th className="text-left px-2 sm:px-3 py-2 whitespace-nowrap font-medium" style={{ color: tokens.charcoal }}>Code</th>
                      <th className="text-left px-2 sm:px-3 py-2 font-medium" style={{ color: tokens.charcoal }}>Description</th>
                      <th className="text-right px-2 sm:px-3 py-2 whitespace-nowrap font-medium" style={{ color: tokens.charcoal }}>Qty</th>
                      <th className="text-right px-2 sm:px-3 py-2 whitespace-nowrap font-medium" style={{ color: tokens.charcoal }}>Price</th>
                      <th className="text-right px-2 sm:px-3 py-2 whitespace-nowrap font-medium" style={{ color: tokens.charcoal }}>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {match.po_data.items.map((item: any, i: number) => (
                      <tr key={i} style={{ borderBottom: `1px solid ${tokens.sand}` }}>
                        <td className="px-2 sm:px-3 py-2 font-mono whitespace-nowrap" style={{ color: tokens.slate }}>{item.item_code}</td>
                        <td className="px-2 sm:px-3 py-2" style={{ color: tokens.charcoal }}>{item.description}</td>
                        <td className="px-2 sm:px-3 py-2 text-right whitespace-nowrap" style={{ color: tokens.slate }}>{item.quantity}</td>
                        <td className="px-2 sm:px-3 py-2 text-right whitespace-nowrap" style={{ color: tokens.slate }}>{formatCurrency(item.unit_price)}</td>
                        <td className="px-2 sm:px-3 py-2 text-right font-medium whitespace-nowrap" style={{ color: tokens.charcoal }}>{formatCurrency(item.total_price)}</td>
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
              <h3 className="text-sm font-semibold mb-2" style={{ color: tokens.crimson }}>
                Discrepancies ({match.discrepancies.length})
              </h3>
              <div className="space-y-2">
                {match.discrepancies.map((d, i) => (
                  <div 
                    key={i} 
                    className="p-3 rounded-xl text-xs" 
                    style={{
                      background: d.severity === 'HIGH' ? `${tokens.crimson}15` : 
                                d.severity === 'MEDIUM' ? `${tokens.amber}15` : `${tokens.mist}15`,
                      border: `1px solid ${d.severity === 'HIGH' ? tokens.crimson : 
                                          d.severity === 'MEDIUM' ? tokens.amber : tokens.mist}`,
                      color: d.severity === 'HIGH' ? tokens.crimson : 
                            d.severity === 'MEDIUM' ? tokens.amber : tokens.slate
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <span 
                        className="px-2 py-0.5 rounded text-[10px] font-bold"
                        style={{
                          background: d.severity === 'HIGH' ? tokens.crimson : tokens.amber,
                          color: 'white'
                        }}
                      >
                        {d.severity}
                      </span>
                      <span className="font-semibold">{d.type}</span>
                    </div>
                    <p className="mt-1.5">{d.message}</p>
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
