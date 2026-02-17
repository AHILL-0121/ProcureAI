'use client';

import { cn } from '@/lib/utils';

/* ─── Base Skeleton Block ─── */
export function Skeleton({ className, style }: { className?: string; style?: React.CSSProperties }) {
  return <div className={cn('skeleton', className)} style={style} />;
}

/* ─── Dashboard KPI Skeleton ─── */
export function KPICardSkeleton() {
  return (
    <div className="glass-card p-5 animate-fade-in">
      <div className="flex items-center gap-4">
        <Skeleton className="h-12 w-12 rounded-xl" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-6 w-28" />
          <Skeleton className="h-3 w-16" />
        </div>
      </div>
    </div>
  );
}

/* ─── Chart Card Skeleton ─── */
export function ChartSkeleton() {
  return (
    <div className="glass-card p-6 animate-fade-in">
      <Skeleton className="h-4 w-32 mb-6" />
      <div className="flex items-end justify-center gap-3 h-[240px] pt-8">
        {[40, 70, 55, 85, 65, 45, 75].map((h, i) => (
          <Skeleton
            key={i}
            className="w-8 rounded-t-md"
            style={{ height: `${h}%`, animationDelay: `${i * 0.1}s` }}
          />
        ))}
      </div>
    </div>
  );
}

/* ─── Table Row Skeleton ─── */
export function TableRowSkeleton({ cols = 6 }: { cols?: number }) {
  return (
    <tr className="border-b border-white/10">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3.5">
          <Skeleton className={cn('h-4', i === 0 ? 'w-24' : i === cols - 1 ? 'w-16' : 'w-20')} />
        </td>
      ))}
    </tr>
  );
}

/* ─── Table Skeleton (full) ─── */
export function TableSkeleton({ rows = 5, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="glass-table overflow-hidden animate-fade-in">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-primary-500/5 border-b border-primary-500/10">
              {Array.from({ length: cols }).map((_, i) => (
                <th key={i} className="px-4 py-3">
                  <Skeleton className="h-3 w-16" />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: rows }).map((_, i) => (
              <TableRowSkeleton key={i} cols={cols} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ─── Match Card Skeleton ─── */
export function MatchCardSkeleton() {
  return (
    <div className="glass-card p-5 animate-fade-in">
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-3 w-24" />
        </div>
        <Skeleton className="h-6 w-24 rounded-full" />
      </div>
      <div className="mt-4 flex items-center gap-4">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-3 w-24" />
      </div>
      <div className="mt-3 pt-3 border-t border-white/20 space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-3/4" />
      </div>
    </div>
  );
}

/* ─── Health Card Skeleton ─── */
export function HealthCardSkeleton() {
  return (
    <div className="glass-card p-4 animate-fade-in">
      <div className="flex items-center gap-3">
        <Skeleton className="h-3 w-3 rounded-full" />
        <div className="space-y-2 flex-1">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-3 w-36" />
        </div>
      </div>
    </div>
  );
}

/* ─── Page Header Skeleton ─── */
export function PageHeaderSkeleton() {
  return (
    <div className="space-y-2 animate-fade-in">
      <Skeleton className="h-7 w-40" />
      <Skeleton className="h-4 w-64" />
    </div>
  );
}

/* ─── Dashboard Full Skeleton ─── */
export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <PageHeaderSkeleton />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger-children">
        <KPICardSkeleton />
        <KPICardSkeleton />
        <KPICardSkeleton />
        <KPICardSkeleton />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 stagger-children">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
      <div className="glass-card p-6 animate-fade-in" style={{ animationDelay: '0.4s' }}>
        <Skeleton className="h-4 w-28 mb-4" />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <HealthCardSkeleton />
          <HealthCardSkeleton />
          <HealthCardSkeleton />
        </div>
      </div>
    </div>
  );
}

/* ─── Invoices Page Skeleton ─── */
export function InvoicesPageSkeleton() {
  return (
    <div className="space-y-6">
      <PageHeaderSkeleton />
      <div className="flex gap-3 animate-fade-in" style={{ animationDelay: '0.1s' }}>
        <Skeleton className="h-10 flex-1 max-w-xs rounded-xl" />
        <Skeleton className="h-10 w-36 rounded-xl" />
      </div>
      <TableSkeleton rows={6} cols={8} />
    </div>
  );
}

/* ─── Matches Page Skeleton ─── */
export function MatchesPageSkeleton() {
  return (
    <div className="space-y-6">
      <PageHeaderSkeleton />
      <div className="flex gap-2 animate-fade-in" style={{ animationDelay: '0.1s' }}>
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-9 w-24 rounded-xl" />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 stagger-children">
        <MatchCardSkeleton />
        <MatchCardSkeleton />
        <MatchCardSkeleton />
        <MatchCardSkeleton />
      </div>
    </div>
  );
}

/* ─── PO Page Skeleton ─── */
export function POPageSkeleton() {
  return (
    <div className="space-y-6">
      <PageHeaderSkeleton />
      <Skeleton className="h-10 w-full max-w-md rounded-xl animate-fade-in" />
      <TableSkeleton rows={8} cols={6} />
    </div>
  );
}
