'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Hl, LedgerSkeleton, Notice, Odometer } from '@/components/ui';
import { get } from '@/lib/api';
import { ISSUE_LABEL, longDate, money, pct } from '@/lib/format';
import type { DashboardStats } from '@/lib/types';

export default function OverviewPage() {
  const q = useQuery({ queryKey: ['stats'], queryFn: () => get<DashboardStats>('/dashboard/stats'), refetchInterval: 60_000 });
  if (q.isLoading) return <div className="screen"><LedgerSkeleton rows={8} /></div>;
  if (q.isError || !q.data) return <div className="screen"><Notice tone="bad">{(q.error as Error)?.message}</Notice></div>;
  const s = q.data;
  const waiting = s.in_review + s.on_hold;
  const decided = s.matched + s.partial_match + s.no_match;
  const maxIssue = Math.max(1, ...s.issues_by_type.map((i) => i.count));

  return (
    <div className="screen">
      <div className="day">
        <section className="sheet intro">
          <p className="label">{longDate()}</p>
          <h1 className="display intro__title">
            {decided === 0
              ? 'No invoices matched yet.'
              : `${s.matched} of ${decided} invoice${decided === 1 ? '' : 's'} matched themselves.`}
          </h1>
          <p className="intro__lede">
            {waiting > 0 ? (
              <>
                <strong><Hl on>{waiting} {waiting === 1 ? 'is' : 'are'} waiting for you</Hl></strong>
                {s.issues_by_type[0] && <>, mostly “{ISSUE_LABEL[s.issues_by_type[0].type] ?? s.issues_by_type[0].type}”</>}.
              </>
            ) : (
              <>Nothing is waiting for a decision.</>
            )}
            {s.processing > 0 && <> {s.processing} more {s.processing === 1 ? 'is' : 'are'} being read right now.</>}
          </p>
          <div className="intro__actions">
            <Link href="/app/in-tray" className="key key--primary">Open the in-tray</Link>
            <span className="muted">Auto-match rate {pct(s.auto_match_rate)} · average read {s.avg_processing_time.toFixed(1)}s</span>
          </div>
        </section>

        <Tape s={s} />
      </div>

      <div className="overview-grid">
        <section className="sheet panel panel--chart">
          <h2 className="label">Last 30 days</h2>
          <InkChart daily={s.daily} />
        </section>

        <section className="sheet panel">
          <h2 className="label">Why invoices are waiting</h2>
          {s.issues_by_type.length === 0 ? <p className="muted">No open exceptions.</p> : (
            <ul className="bars">
              {s.issues_by_type.map((i, n) => (
                <li key={i.type}>
                  <span>{ISSUE_LABEL[i.type] ?? i.type}</span>
                  <span className="num">{i.count}</span>
                  <span className={`bar ${n % 2 ? 'bar--hatch' : ''}`}><i style={{ width: `${(i.count / maxIssue) * 100}%` }} /></span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="sheet panel">
          <h2 className="label">Vendors to watch</h2>
          {s.vendors_to_watch.length === 0 ? <p className="muted">No vendor has open exceptions.</p> : (
            <ol className="ruled-list">
              {s.vendors_to_watch.map((v) => (
                <li key={v.vendor}>
                  <span>{v.vendor}</span>
                  <span className="num muted">{v.open_exceptions} open</span>
                </li>
              ))}
            </ol>
          )}
          <h2 className="label panel__sub">Waiting, by currency</h2>
          {s.held_by_currency.length === 0 ? <p className="muted">—</p> : (
            <ol className="ruled-list">
              {s.held_by_currency.map((c) => (
                <li key={c.currency}><span className="num">{c.currency}</span><span className="num">{money(c.amount)}</span></li>
              ))}
            </ol>
          )}
        </section>
      </div>
    </div>
  );
}

function Tape({ s }: { s: DashboardStats }) {
  const lines: [string, number][] = [
    ['RECEIVED TODAY', s.today.received],
    ['AUTO-MATCHED', s.today.auto_matched],
    ['APPROVED BY PEOPLE', s.today.approved],
    ['REJECTED', s.today.rejected],
    ['WAITING', s.today.waiting],
  ];
  return (
    <div className="tape" aria-label="Today's totals">
      {lines.map(([k, v], i) => (
        <div className="tape__ln" key={k} style={{ ['--i' as string]: i }}>
          <span>{k}</span><span className="tape__dots" /><Odometer value={String(v)} />
        </div>
      ))}
      <div className="tape__rule" />
      <div className="tape__ln tape__cur" style={{ ['--i' as string]: 6 }}><span>VALUE CLEARED</span></div>
      {s.cleared_by_currency.length === 0 && <div className="tape__ln tape__tot" style={{ ['--i' as string]: 7 }}><span>—</span></div>}
      {s.cleared_by_currency.slice(0, 4).map((c, i) => (
        <div className="tape__ln tape__tot" key={c.currency} style={{ ['--i' as string]: 7 + i }}>
          <span>{c.currency}</span><Odometer value={money(c.amount)} />
        </div>
      ))}
    </div>
  );
}

/** Ink-on-ledger line chart: received vs exceptions per day. */
function InkChart({ daily }: { daily: DashboardStats['daily'] }) {
  const W = 640, H = 200, L = 34, R = 12, T = 12, B = 26;
  if (daily.length === 0) return <p className="muted">No invoices in the last 30 days.</p>;
  const max = Math.max(4, ...daily.map((d) => d.received));
  const step = Math.ceil(max / 4);
  const top = step * 4;
  const x = (i: number) => L + (daily.length === 1 ? (W - L - R) / 2 : (i * (W - L - R)) / (daily.length - 1));
  const y = (v: number) => T + (H - T - B) * (1 - v / top);
  const path = (key: 'received' | 'exceptions' | 'auto_matched') => daily.map((d, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(d[key]).toFixed(1)}`).join(' ');
  const ticks = [0, 1, 2, 3, 4].map((n) => n * step);
  const last = daily[daily.length - 1];
  const labelEvery = Math.max(1, Math.ceil(daily.length / 6));
  return (
    <figure className="inkchart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Invoices received and exceptions per day, last ${daily.length} days`}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={L} x2={W - R} y1={y(t)} y2={y(t)} className="inkchart__rule" />
            <text x={L - 8} y={y(t) + 4} className="inkchart__tick" textAnchor="end">{t}</text>
          </g>
        ))}
        <line x1={L - 2} x2={L - 2} y1={T - 6} y2={H - B} className="inkchart__margin" />
        <line x1={L + 1} x2={L + 1} y1={T - 6} y2={H - B} className="inkchart__margin" />
        {daily.map((d, i) => (i % labelEvery === 0 || i === daily.length - 1) && (
          <text key={d.date} x={x(i)} y={H - 8} className="inkchart__tick" textAnchor="middle">{d.date.slice(5)}</text>
        ))}
        <path d={`${path('received')} L${x(daily.length - 1)},${y(0)} L${x(0)},${y(0)} Z`} className="inkchart__wash" />
        <path d={path('received')} className="inkchart__line" />
        <path d={path('exceptions')} className="inkchart__line inkchart__line--bad" />
        <circle cx={x(daily.length - 1)} cy={y(last.received)} r="3.5" className="inkchart__dot" />
        <circle cx={x(daily.length - 1)} cy={y(last.exceptions)} r="3.5" className="inkchart__dot inkchart__dot--bad" />
      </svg>
      <figcaption className="inkchart__legend">
        <span><i className="sw sw--carbon" /> Received</span>
        <span><i className="sw sw--bad" /> Exceptions</span>
      </figcaption>
    </figure>
  );
}
