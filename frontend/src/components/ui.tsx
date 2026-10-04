'use client';

import { forwardRef, useEffect, useMemo, useRef, useState, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { CheckCircle, Clock, Info, MinusCircle, Warning, XCircle } from '@phosphor-icons/react';
import { RESULT, SEVERITY_TONE, STATUS, money } from '@/lib/format';
import type { InvoiceStatus, MatchResult, Severity } from '@/lib/types';

type Tone = 'ok' | 'hold' | 'bad' | 'info' | 'pencil';

const TONE_ICON: Record<Tone, ReactNode> = {
  ok: <CheckCircle weight="bold" aria-hidden />,
  hold: <Warning weight="bold" aria-hidden />,
  bad: <XCircle weight="bold" aria-hidden />,
  info: <Clock weight="bold" aria-hidden />,
  pencil: <MinusCircle weight="bold" aria-hidden />,
};

/** SVG filter that gives stamps and ink marks an uneven, pressed-ink texture. Render once. */
export function InkDefs() {
  return (
    <svg width="0" height="0" style={{ position: 'absolute' }} aria-hidden="true" focusable="false">
      <defs>
        <filter id="ink" x="-10%" y="-20%" width="120%" height="140%">
          <feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="7" result="n" />
          <feColorMatrix in="n" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -3 2.35" result="m" />
          <feComposite in="SourceGraphic" in2="m" operator="in" result="c" />
          <feTurbulence type="fractalNoise" baseFrequency=".04" numOctaves="1" seed="3" result="w" />
          <feDisplacementMap in="c" in2="w" scale="2.2" />
        </filter>
      </defs>
    </svg>
  );
}

export function StatusInk({ status, result, severity, label, tone, className = '' }: {
  status?: InvoiceStatus; result?: MatchResult; severity?: Severity; label?: string; tone?: Tone; className?: string;
}) {
  const meta = status ? STATUS[status] : result ? RESULT[result] : severity ? { label: severity.toLowerCase(), tone: SEVERITY_TONE[severity] } : null;
  const t = tone ?? meta?.tone ?? 'pencil';
  return (
    <span className={`ink ink--${t} ${className}`}>
      {TONE_ICON[t]}
      <span>{label ?? meta?.label}</span>
    </span>
  );
}

export function Blot({ severity }: { severity?: Severity | null }) {
  if (!severity) return <span className="blot blot--none" aria-hidden />;
  return <span className={`blot blot--${SEVERITY_TONE[severity]}`} title={`${severity.toLowerCase()} severity`} />;
}

type KeyVariant = 'primary' | 'plain' | 'danger' | 'ghost';

export const Key = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & { variant?: KeyVariant; busy?: boolean; size?: 'sm' | 'md' }>(
  function Key({ variant = 'plain', busy, size = 'md', className = '', children, disabled, ...rest }, ref) {
    return (
      <button
        ref={ref}
        type="button"
        className={`key key--${variant} key--${size} ${busy ? 'is-busy' : ''} ${className}`}
        disabled={disabled || busy}
        aria-busy={busy || undefined}
        {...rest}
      >
        {children}
      </button>
    );
  },
);

export function Money({ amount, currency, className = '' }: { amount: number | null | undefined; currency?: string | null; className?: string }) {
  return (
    <span className={`money num ${className}`}>
      {currency && <span className="money__cur">{currency}</span>}
      {money(amount)}
    </span>
  );
}

/** A rubber stamp. `drop` plays the landing animation once when it first mounts. */
export function Stamp({ text, sub, tone, drop = false, seed = 0, className = '' }: {
  text: string; sub?: string; tone: 'ok' | 'hold' | 'bad'; drop?: boolean; seed?: number; className?: string;
}) {
  const rot = useMemo(() => {
    const x = Math.sin((seed + 1) * 9301) * 10000;
    return (x - Math.floor(x)) * 10 - 6;
  }, [seed]);
  return (
    <div className={`stamp stamp--${tone} ${drop ? 'stamp--drop' : ''} ${className}`} style={{ ['--r' as string]: `${rot.toFixed(1)}deg` }} role="img" aria-label={`${text}${sub ? ` — ${sub}` : ''}`}>
      {text}
      {sub && <small>{sub}</small>}
    </div>
  );
}

/** Adding-machine style rolling digits. */
export function Odometer({ value, className = '' }: { value: string; className?: string }) {
  const [shown, setShown] = useState(value);
  useEffect(() => {
    const id = requestAnimationFrame(() => setShown(value));
    return () => cancelAnimationFrame(id);
  }, [value]);
  return (
    <span className={`odo num ${className}`} aria-label={value}>
      {shown.split('').map((ch, i) =>
        /\d/.test(ch) ? (
          <span className="odo__d" key={`${i}-${shown.length}`} aria-hidden>
            <span className="odo__reel" style={{ transform: `translateY(${-1.2 * Number(ch)}em)` }}>
              {Array.from({ length: 10 }, (_, n) => <span key={n}>{n}</span>)}
            </span>
          </span>
        ) : (
          <span key={`${i}-${shown.length}`} aria-hidden>{ch}</span>
        ),
      )}
    </span>
  );
}

/** Red-pencil circle drawn around its children. */
export function PencilCircle({ children, note, tone = 'bad', active = true }: { children: ReactNode; note?: string; tone?: 'bad' | 'hold'; active?: boolean }) {
  return (
    <span className={`pencil pencil--${tone} ${active ? 'is-on' : ''}`}>
      <span className="pencil__target">
        {children}
        <svg viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden>
          <path d="M8,22 C6,8 40,2 72,5 C96,8 99,30 78,35 C52,41 10,38 5,25 C3,18 12,11 22,9" />
        </svg>
      </span>
      {note && <span className="pencil__note hand">{note}</span>}
    </span>
  );
}

export function Hl({ children, on = false }: { children: ReactNode; on?: boolean }) {
  return <span className={`hl ${on ? 'hl--on' : ''}`}>{children}</span>;
}

export function Sheet({ children, className = '', tint, as: As = 'section', ...rest }: {
  children: ReactNode; className?: string; tint?: 'white' | 'canary' | 'pink'; as?: 'section' | 'div' | 'article' | 'aside';
} & React.HTMLAttributes<HTMLElement>) {
  return <As className={`sheet ${tint ? `sheet--${tint}` : ''} ${className}`} {...rest}>{children}</As>;
}

/** Paper-tray empty state with a gentle pointer parallax. */
export function EmptyTray({ title, children }: { title: string; children?: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const move = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      const x = ((e.clientX - r.left) / r.width - 0.5) * 12;
      const y = ((e.clientY - r.top) / r.height - 0.5) * 8;
      el.style.setProperty('--px', `${x.toFixed(1)}px`);
      el.style.setProperty('--py', `${y.toFixed(1)}px`);
    };
    el.addEventListener('pointermove', move);
    return () => el.removeEventListener('pointermove', move);
  }, []);
  return (
    <div className="empty" ref={ref}>
      <svg className="empty__tray" viewBox="0 0 160 90" aria-hidden>
        <rect className="empty__sheet" x="38" y="8" width="84" height="56" rx="2" />
        <path className="empty__lines" d="M50 22h50M50 30h60M50 38h40" />
        <path className="empty__box" d="M10 50h38l6 12h52l6-12h38v30H10z" />
      </svg>
      <b className="display">{title}</b>
      {children && <p>{children}</p>}
    </div>
  );
}

export function LedgerSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="ledger-skel" aria-hidden>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="ledger-skel__row" style={{ animationDelay: `${i * 80}ms` }}>
          <span style={{ width: `${30 + ((i * 37) % 40)}%` }} />
        </div>
      ))}
    </div>
  );
}

export function Notice({ tone = 'info', children }: { tone?: 'info' | 'bad' | 'hold'; children: ReactNode }) {
  return (
    <div className={`notice notice--${tone}`} role={tone === 'bad' ? 'alert' : undefined}>
      <Info weight="bold" aria-hidden />
      <div>{children}</div>
    </div>
  );
}
