'use client';

import { useEffect, useState } from 'react';
import { apiFetch, formatCurrency, cn } from '@/lib/utils';
import { useWebSocket } from '@/components/WebSocketProvider';
import { DashboardSkeleton } from '@/components/Skeletons';
import type { DashboardStats, HealthStatus } from '@/lib/types';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';

const COLORS = ['#10b981', '#f59e0b', '#ef4444', '#94a3b8'];

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const { lastMessage } = useWebSocket();

  const fetchData = async () => {
    try {
      const [s, h] = await Promise.all([
        apiFetch<DashboardStats>('/dashboard/stats'),
        apiFetch<HealthStatus>('/health'),
      ]);
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
        <h1 className="text-2xl font-bold bg-gradient-to-r from-surface-900 to-surface-600 bg-clip-text text-transparent">
          Dashboard
        </h1>
        <p className="text-sm text-surface-400 mt-1">Real-time overview of procurement automation</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger-children">
        <KPICard
          title="Total Invoices"
          value={stats?.total_invoices ?? 0}
          subtitle="Processed"
          gradient="from-sky-400 to-cyan-500"
          icon={<InvoiceIcon />}
        />
        <KPICard
          title="Fully Matched"
          value={stats?.matched ?? 0}
          subtitle={stats && stats.total_invoices > 0 ? `${Math.round((stats.matched / stats.total_invoices) * 100)}% rate` : '-'}
          gradient="from-emerald-400 to-teal-500"
          icon={<CheckIcon />}
        />
        <KPICard
          title="Total Value"
          value={formatCurrency(stats?.total_value ?? 0)}
          subtitle="Invoice value"
          gradient="from-amber-400 to-orange-500"
          icon={<CurrencyIcon />}
        />
        <KPICard
          title="Avg Processing"
          value={`${stats?.avg_processing_time?.toFixed(1) ?? '0'}s`}
          subtitle={`${stats?.avg_confidence ? (stats.avg_confidence * 100).toFixed(0) : 0}% confidence`}
          gradient="from-teal-400 to-emerald-500"
          icon={<SpeedIcon />}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Match Distribution Pie */}
        <div className="glass-card p-6 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
          <h3 className="text-sm font-semibold text-surface-600 mb-4 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-gradient-to-r from-primary-400 to-accent-400" />
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
                    background: 'rgba(255,255,255,0.8)',
                    backdropFilter: 'blur(12px)',
                    border: '1px solid rgba(255,255,255,0.4)',
                    borderRadius: '12px',
                    boxShadow: '0 4px 16px rgba(0,0,0,0.06)',
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-60 text-surface-400 text-sm">
              No data yet - upload invoices to get started
            </div>
          )}
        </div>

        {/* Match Results Bar */}
        <div className="glass-card p-6 animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
          <h3 className="text-sm font-semibold text-surface-600 mb-4 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-gradient-to-r from-accent-400 to-primary-400" />
            Match Results
          </h3>
          {barData.some(d => d.count > 0) ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.05)" />
                <XAxis dataKey="name" fontSize={12} stroke="#94a3b8" />
                <YAxis allowDecimals={false} fontSize={12} stroke="#94a3b8" />
                <Tooltip
                  contentStyle={{
                    background: 'rgba(255,255,255,0.8)',
                    backdropFilter: 'blur(12px)',
                    border: '1px solid rgba(255,255,255,0.4)',
                    borderRadius: '12px',
                    boxShadow: '0 4px 16px rgba(0,0,0,0.06)',
                  }}
                />
                <Bar dataKey="count" fill="url(#barGradient)" radius={[8, 8, 0, 0]} />
                <defs>
                  <linearGradient id="barGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#10b981" />
                    <stop offset="100%" stopColor="#14b8a6" />
                  </linearGradient>
                </defs>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-60 text-surface-400 text-sm">
              No data yet - upload invoices to get started
            </div>
          )}
        </div>
      </div>

      {/* System Health */}
      {health && (
        <div className="glass-card p-6 animate-fade-in-up" style={{ animationDelay: '0.4s' }}>
          <h3 className="text-sm font-semibold text-surface-600 mb-4 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse-green" />
            System Health
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <HealthCard
              label="Ollama / Llama 3.1"
              status={health.vision_ocr.ollama_status === 'online' && health.vision_ocr.model_available}
              detail={health.vision_ocr.model_available
                ? `Model: ${health.vision_ocr.model}`
                : health.vision_ocr.error || 'Model not found'}
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

function KPICard({ title, value, subtitle, gradient, icon }: {
  title: string; value: string | number; subtitle: string; gradient: string; icon: React.ReactNode;
}) {
  return (
    <div className="glass-card p-5 group">
      <div className="flex items-center gap-4">
        <div className={cn(
          'h-12 w-12 rounded-xl flex items-center justify-center text-white shadow-lg transition-transform duration-300 group-hover:scale-110 group-hover:rotate-3',
          `bg-gradient-to-br ${gradient}`
        )}>
          {icon}
        </div>
        <div>
          <p className="text-xs text-surface-400 uppercase tracking-wider font-medium">{title}</p>
          <p className="text-xl font-bold text-surface-800 mt-0.5">{value}</p>
          <p className="text-xs text-surface-400">{subtitle}</p>
        </div>
      </div>
    </div>
  );
}

function HealthCard({ label, status, detail }: { label: string; status: boolean; detail: string }) {
  return (
    <div className="flex items-center gap-3 p-4 rounded-xl glass group hover:glow-emerald transition-all duration-300">
      <span className={cn(
        'h-3 w-3 rounded-full transition-all duration-300',
        status ? 'bg-emerald-500 shadow-lg shadow-emerald-500/40' : 'bg-red-500 shadow-lg shadow-red-500/40'
      )} />
      <div>
        <p className="text-sm font-medium text-surface-700">{label}</p>
        <p className="text-xs text-surface-400">{detail}</p>
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
