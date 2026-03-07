'use client';

import { useEffect, useState } from 'react';
import { apiFetch, formatCurrency, cn } from '@/lib/utils';
import { useWebSocket } from '@/components/WebSocketProvider';
import { DashboardSkeleton } from '@/components/Skeletons';
import type { DashboardStats, HealthStatus } from '@/lib/types';
import { tokens } from '@/lib/design-tokens';
import { TiltCard, AnimCounter } from '@/components/UIComponents';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';

const COLORS = [tokens.forest, tokens.gold, tokens.crimson, tokens.mist];

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchTime, setFetchTime] = useState<number>(0);
  const { lastMessage } = useWebSocket();

  const fetchData = async () => {
    const startTime = performance.now();
    try {
      const [s, h] = await Promise.all([
        apiFetch<DashboardStats>('/dashboard/stats'),
        apiFetch<HealthStatus>('/health'),
      ]);
      const endTime = performance.now();
      setFetchTime(Math.round(endTime - startTime));
      setStats(s);
      setHealth(h);
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchData(); }, []);
  useEffect(() => {
    if (lastMessage?.event === 'match_complete') fetchData();
  }, [lastMessage]);

  if (loading) return <DashboardSkeleton />;

  const pieData = stats ? [
    { name: 'Matched', value: stats.matched },
    { name: 'Partial', value: stats.partial_match },
    { name: 'No Match', value: stats.no_match },
    { name: 'Pending', value: stats.pending },
  ].filter(d => d.value > 0) : [];

  const barData = stats ? [
    { name: 'Matched', count: stats.matched },
    { name: 'Partial', count: stats.partial_match },
    { name: 'No Match', count: stats.no_match },
    { name: 'Failed', count: stats.failed },
  ] : [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Title */}
      <div className="animate-fade-in-down">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold" style={{
              background: `linear-gradient(to right, ${tokens.charcoal}, ${tokens.slate})`,
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text'
            }}>
              Dashboard
            </h1>
            <p className="text-sm mt-1" style={{ color: tokens.mist }}>Real-time overview of procurement automation</p>
          </div>
          {fetchTime > 0 && (
            <div className="text-xs px-3 py-1.5 rounded-lg" style={{ 
              background: fetchTime < 200 ? `${tokens.forest}20` : fetchTime < 500 ? `${tokens.amber}20` : `${tokens.crimson}20`,
              color: fetchTime < 200 ? tokens.forest : fetchTime < 500 ? tokens.amber : tokens.crimson,
              border: `1px solid ${fetchTime < 200 ? tokens.forest : fetchTime < 500 ? tokens.amber : tokens.crimson}40`
            }}>
              ⚡ Data fetched in {fetchTime}ms
            </div>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger-children">
        <KPICard
          title="Total Invoices"
          value={stats?.total_invoices ?? 0}
          subtitle="Processed"
          icon="🧾"
          delay={0}
        />
        <KPICard
          title="Fully Matched"
          value={stats?.matched ?? 0}
          subtitle={stats && stats.total_invoices > 0 ? `${Math.round((stats.matched / stats.total_invoices) * 100)}% rate` : '-'}
          icon="✅"
          delay={80}
        />
        <KPICard
          title="Total Value"
          value={formatCurrency(stats?.total_value ?? 0)}
          subtitle="Invoice value"
          icon="💰"
          delay={160}
        />
        <KPICard
          title="Avg Processing"
          value={`${stats?.avg_processing_time?.toFixed(1) ?? '0'}s`}
          subtitle={`${stats?.avg_confidence ? (stats.avg_confidence * 100).toFixed(0) : 0}% confidence`}
          icon="⏱"
          delay={240}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Match Distribution Pie */}
        <div className="warm-card p-6 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: tokens.slate }}>
            <span className="h-2 w-2 rounded-full" style={{ background: tokens.amber }} />
            Match Distribution
          </h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} dataKey="value" label
                  strokeWidth={2} stroke="rgba(255,255,255,0.8)">
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Legend />
                <Tooltip
                  contentStyle={{
                    background: 'white',
                    border: `1.5px solid ${tokens.sand}`,
                    borderRadius: '12px',
                    boxShadow: `0 4px 16px ${tokens.sand}60`,
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-60 text-sm" style={{ color: tokens.mist }}>
              No data yet - upload invoices to get started
            </div>
          )}
        </div>

        {/* Match Results Bar */}
        <div className="warm-card p-6 animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: tokens.slate }}>
            <span className="h-2 w-2 rounded-full" style={{ background: tokens.forest }} />
            Match Results
          </h3>
          {barData.some(d => d.count > 0) ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke={tokens.sand} />
                <XAxis dataKey="name" fontSize={12} stroke={tokens.mist} />
                <YAxis allowDecimals={false} fontSize={12} stroke={tokens.mist} />
                <Tooltip
                  contentStyle={{
                    background: 'white',
                    border: `1.5px solid ${tokens.sand}`,
                    borderRadius: '12px',
                    boxShadow: `0 4px 16px ${tokens.sand}60`,
                  }}
                />
                <Bar dataKey="count" fill="url(#barGradient)" radius={[8, 8, 0, 0]} />
                <defs>
                  <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={tokens.amber} />
                    <stop offset="100%" stopColor={tokens.ember} />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-60 text-sm" style={{ color: tokens.mist }}>
              No data yet - upload invoices to get started
            </div>
          )}
        </div>
      </div>

      {/* System Health */}
      {health && (
        <div className="warm-card p-6 animate-fade-in-up" style={{ animationDelay: '0.4s' }}>
          <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: tokens.slate }}>
            <span className="h-2 w-2 rounded-full animate-pulse" style={{ background: tokens.forest }} />
            System Health
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <HealthCard
              label="Groq API (Llama 3.3)"
              status={health.vision_ocr.groq_status === 'online' && health.vision_ocr.model_available}
              detail={health.vision_ocr.model_available
                ? `${health.vision_ocr.model} + vision`
                : health.vision_ocr.error || 'API not configured'}
            />
            <HealthCard
              label="ERP Dataset"
              status={true}
              detail={`${health.erp.total_purchase_orders} POs | ${health.erp.unique_vendors} Vendors`}
            />
            <HealthCard
              label="Orchestrator"
              status={health.orchestrator === 'healthy'}
              detail={`${health.erp.total_goods_receipts} GRNs | ${health.erp.total_po_lines || ''} Lines`}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function KPICard({ title, value, subtitle, icon, delay }: {
  title: string; value: string | number; subtitle: string; icon: string; delay: number;
}) {
  return (
    <div className="animate-fade-in-up" style={{ animationDelay: `${delay}ms` }}>
      <TiltCard className="warm-card p-5 group">
        <div className="flex items-center gap-4">
          <div
            className="h-12 w-12 rounded-xl flex items-center justify-center text-white shadow-lg transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3"
            style={{
              background: `linear-gradient(135deg, ${tokens.amber}, ${tokens.ember})`,
              fontSize: 24
            }}
          >
            {icon}
          </div>
          <div>
            <p className="text-xs uppercase tracking-wider font-medium" style={{ color: tokens.mist }}>{title}</p>
            <p className="text-xl font-bold mt-0.5" style={{ color: tokens.charcoal }}>
              {typeof value === 'number' ? <AnimCounter to={value} /> : value}
            </p>
            <p className="text-xs" style={{ color: tokens.mist }}>{subtitle}</p>
          </div>
        </div>
      </TiltCard>
    </div>
  );
}

function HealthCard({ label, status, detail }: { label: string; status: boolean; detail: string }) {
  return (
    <div
      className="flex items-center gap-3 p-4 rounded-xl transition-all duration-300"
      style={{
        background: tokens.parchment,
        border: `1px solid ${tokens.sand}`
      }}
    >
      <span
        className="h-3 w-3 rounded-full transition-all duration-300"
        style={{
          background: status ? tokens.forest : tokens.crimson,
          boxShadow: status ? `0 0 8px ${tokens.forest}60` : `0 0 8px ${tokens.crimson}60`
        }}
      />
      <div>
        <p className="text-sm font-medium" style={{ color: tokens.charcoal }}>{label}</p>
        <p className="text-xs" style={{ color: tokens.mist }}>{detail}</p>
      </div>
    </div>
  );
}

/* Mini icons for KPI cards */
function InvoiceIcon() {
  return (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
    </svg>
  );
}
function CheckIcon() {
  return (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}
function CurrencyIcon() {
  return (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  );
}
function SpeedIcon() {
  return (
    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
    </svg>
  );
}
