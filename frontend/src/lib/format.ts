import type { InvoiceStatus, MatchResult, Severity } from './types';

export function money(amount: number | null | undefined, currency?: string | null): string {
  if (amount === null || amount === undefined || Number.isNaN(amount)) return '—';
  const n = new Intl.NumberFormat('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(amount);
  return currency ? `${currency} ${n}` : n;
}

export function qty(n: number | null | undefined): string {
  if (n === null || n === undefined) return '—';
  return new Intl.NumberFormat('en-GB', { maximumFractionDigits: 3 }).format(n);
}

export function pct(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined) return '—';
  return `${(n * 100).toFixed(digits)}%`;
}

export function signedPct(n: number | null | undefined): string {
  if (n === null || n === undefined) return '';
  return `${n > 0 ? '+' : ''}${n.toFixed(1)}%`;
}

export function date(value: string | null | undefined, opts: Intl.DateTimeFormatOptions = { day: '2-digit', month: 'short', year: 'numeric' }): string {
  if (!value) return '—';
  const d = new Date(value.length === 10 ? `${value}T00:00:00` : value);
  return Number.isNaN(d.getTime()) ? value : d.toLocaleDateString('en-GB', opts);
}

export function time(value: string | null | undefined): string {
  if (!value) return '';
  const d = new Date(value);
  return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

export function age(value: string | null | undefined): string {
  if (!value) return '';
  const ms = Date.now() - new Date(value).getTime();
  const m = Math.floor(ms / 60000);
  if (m < 1) return 'now';
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}

export function longDate(d = new Date()): string {
  return d.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
}

type Tone = 'ok' | 'hold' | 'bad' | 'info' | 'pencil';

export const STATUS: Record<InvoiceStatus, { label: string; tone: Tone }> = {
  RECEIVED: { label: 'Received', tone: 'info' },
  EXTRACTING: { label: 'Reading', tone: 'info' },
  EXTRACTED: { label: 'Read', tone: 'info' },
  VALIDATING: { label: 'Checking', tone: 'info' },
  VALIDATED: { label: 'Checked', tone: 'info' },
  MATCHING: { label: 'Matching', tone: 'info' },
  MATCHED: { label: 'Matched', tone: 'ok' },
  DISCREPANCY: { label: 'Needs review', tone: 'hold' },
  ON_HOLD: { label: 'On hold', tone: 'hold' },
  APPROVED: { label: 'Approved', tone: 'ok' },
  REJECTED: { label: 'Rejected', tone: 'bad' },
  DUPLICATE: { label: 'Duplicate', tone: 'bad' },
  FAILED: { label: 'Could not read', tone: 'bad' },
};

export const RESULT: Record<MatchResult, { label: string; tone: Tone }> = {
  FULL_MATCH: { label: 'Full match', tone: 'ok' },
  PARTIAL_MATCH: { label: 'Partial match', tone: 'hold' },
  NO_MATCH: { label: 'No match', tone: 'bad' },
  PENDING: { label: 'Pending', tone: 'pencil' },
};

export const SEVERITY_TONE: Record<Severity, Tone> = { HIGH: 'bad', MEDIUM: 'hold', LOW: 'pencil' };

/** Plain-language names for discrepancy codes. */
export const ISSUE_LABEL: Record<string, string> = {
  PRICE_OVER: 'Price over PO',
  PRICE_UNDER: 'Price under PO',
  QTY_EXCEEDS_RECEIVED: 'More than received',
  QTY_EXCEEDS_PO: 'More than ordered',
  NOT_RECEIVED: 'Goods not received',
  UNMATCHED_LINE: 'Line not on PO',
  VENDOR_MISMATCH: 'Vendor differs',
  VENDOR_UNVERIFIED: 'Vendor unverified',
  CURRENCY_MISMATCH: 'Currency differs',
  CURRENCY_MISSING: 'No currency',
  MISSING_PO: 'PO not found',
  MISSING_PO_REFERENCE: 'No PO number',
  PO_CLOSED: 'PO closed',
  TOTAL_MISMATCH: 'Unitemised charges',
  UOM_MISMATCH: 'Unit differs',
  DUPLICATE: 'Duplicate',
  VALIDATION_ERROR: 'Missing field',
  LOW_CONFIDENCE: 'Low reading confidence',
  NO_LINES: 'No lines read',
  CREDIT_NOTE: 'Credit note',
  FAILED: 'Could not read',
};

export const IN_FLIGHT: InvoiceStatus[] = ['RECEIVED', 'EXTRACTING', 'EXTRACTED', 'VALIDATING', 'VALIDATED', 'MATCHING'];

export function roleLabel(role: string): string {
  return { viewer: 'Viewer', ap_clerk: 'AP clerk', approver: 'Approver', admin: 'Administrator' }[role] ?? role;
}

export const can = {
  edit: (role?: string) => role === 'ap_clerk' || role === 'approver' || role === 'admin',
  decide: (role?: string) => role === 'approver' || role === 'admin',
  admin: (role?: string) => role === 'admin',
};
