'use client';

import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ErpConnect } from '@/components/ErpConnect';
import { Key, Notice } from '@/components/ui';
import { FxSwitch } from '@/components/shell/TopBar';
import { del, get, patch, post, put } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import { can, date, roleLabel } from '@/lib/format';
import { usePrefs } from '@/lib/prefs';
import { useRealtime } from '@/lib/realtime';
import { useToast } from '@/lib/toast';
import type { Tolerance, UploadItem, User, VendorRef } from '@/lib/types';

export default function SettingsPage() {
  const { user } = useAuth();
  const admin = can.admin(user?.role);
  return (
    <div className="screen form-page">
      <div className="screen__head">
        <div>
          <p className="label">Form PA-1 · Settings</p>
          <h1 className="display screen__title">Settings</h1>
        </div>
      </div>
      <Section n={1} title="ERP connection" lede="The vendors, purchase orders and goods receipts every invoice is matched against.">
        <ErpConnect admin={admin} />
      </Section>
      <Tolerances admin={admin} />
      <EmailIntake admin={admin} />
      {admin && <Users me={user!} />}
      <Preferences />
      {admin && <Demo />}
    </div>
  );
}

function Section({ n, title, lede, children }: { n: number; title: string; lede?: string; children: React.ReactNode }) {
  return (
    <section className="sheet form-section">
      <header className="form-section__head">
        <span className="form-section__n num">§{n}</span>
        <div>
          <h2 className="display">{title}</h2>
          {lede && <p className="muted">{lede}</p>}
        </div>
      </header>
      {children}
    </section>
  );
}

function Ruler({ id, label, value, onChange, min, max, stepValue, format, disabled }: {
  id: string; label: string; value: number; onChange: (v: number) => void; min: number; max: number; stepValue: number; format: (v: number) => string; disabled?: boolean;
}) {
  return (
    <div className="ruler">
      <label className="label" htmlFor={id}>{label}</label>
      <input id={id} type="range" min={min} max={max} step={stepValue} value={value} disabled={disabled} onChange={(e) => onChange(Number(e.target.value))} />
      <output htmlFor={id} className="num">{format(value)}</output>
    </div>
  );
}

function ToleranceForm({ initial, admin, onSave, onRemove, title }: {
  initial: Tolerance; admin: boolean; onSave: (t: Tolerance) => Promise<void>; onRemove?: () => Promise<void>; title: string;
}) {
  const [t, setT] = useState(initial);
  const [busy, setBusy] = useState(false);
  useEffect(() => setT(initial), [initial]);
  const dirty = JSON.stringify(t) !== JSON.stringify(initial);
  const idp = (initial.vendor_id ?? 'default').replace(/\W/g, '');
  return (
    <div className="tol">
      <p className="tol__title">{title}{initial.updated_by && <span className="muted small"> · changed by {initial.updated_by} {date(initial.updated_at)}</span>}</p>
      <Ruler id={`qp-${idp}`} label="Quantity ±" min={0} max={0.1} stepValue={0.005} value={t.qty_pct} disabled={!admin} format={(v) => `${(v * 100).toFixed(1)}%`} onChange={(v) => setT({ ...t, qty_pct: v })} />
      <Ruler id={`pp-${idp}`} label="Unit price ±" min={0} max={0.2} stepValue={0.005} value={t.price_pct} disabled={!admin} format={(v) => `${(v * 100).toFixed(1)}%`} onChange={(v) => setT({ ...t, price_pct: v })} />
      <Ruler id={`pa-${idp}`} label="Price slack (min)" min={0} max={5} stepValue={0.05} value={t.price_abs} disabled={!admin} format={(v) => v.toFixed(2)} onChange={(v) => setT({ ...t, price_abs: v })} />
      <Ruler id={`ta-${idp}`} label="Header total slack" min={0} max={50} stepValue={0.5} value={t.total_abs} disabled={!admin} format={(v) => v.toFixed(2)} onChange={(v) => setT({ ...t, total_abs: v })} />
      {admin && (
        <div className="tol__actions">
          {onRemove && <Key size="sm" variant="ghost" onClick={async () => { setBusy(true); try { await onRemove(); } finally { setBusy(false); } }}>Remove override</Key>}
          <Key size="sm" variant="primary" disabled={!dirty} busy={busy} onClick={async () => { setBusy(true); try { await onSave(t); } finally { setBusy(false); } }}>Save</Key>
        </div>
      )}
    </div>
  );
}

function Tolerances({ admin }: { admin: boolean }) {
  const qc = useQueryClient();
  const { toast } = useToast();
  const q = useQuery({ queryKey: ['tolerances'], queryFn: () => get<{ default: Tolerance; vendors: Tolerance[] }>('/settings/tolerances') });
  const vendors = useQuery({ queryKey: ['vendors'], queryFn: () => get<VendorRef[]>('/vendors'), enabled: admin });
  const [newVendor, setNewVendor] = useState('');

  const save = async (t: Tolerance, vendorId?: string | null) => {
    try {
      await put(`/settings/tolerances${vendorId ? `?vendor_id=${encodeURIComponent(vendorId)}` : ''}`,
        { qty_pct: t.qty_pct, price_pct: t.price_pct, price_abs: t.price_abs, total_abs: t.total_abs });
      qc.invalidateQueries({ queryKey: ['tolerances'] });
      toast('Tolerances saved. They apply to the next match or re-match.');
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Could not save', { tone: 'error' });
    }
  };

  const overridden = new Set((q.data?.vendors ?? []).map((v) => v.vendor_id));
  return (
    <Section n={2} title="Matching tolerances" lede="How far an invoice may differ from the PO and receipt before it needs a person.">
      {q.isError && <Notice tone="bad">{(q.error as Error).message}</Notice>}
      {q.data && <ToleranceForm title="Everyone (default)" initial={q.data.default} admin={admin} onSave={(t) => save(t)} />}
      {q.data?.vendors.map((v) => (
        <ToleranceForm key={v.vendor_id} title={v.vendor_name ?? v.vendor_id ?? 'Vendor'} initial={v} admin={admin}
          onSave={(t) => save(t, v.vendor_id)}
          onRemove={async () => { await del(`/settings/tolerances/${v.vendor_id}`); qc.invalidateQueries({ queryKey: ['tolerances'] }); toast('Override removed'); }} />
      ))}
      {admin && vendors.data && (
        <div className="inline-form">
          <label className="label" htmlFor="new-override">Add a vendor override</label>
          <select id="new-override" className="input" value={newVendor} onChange={(e) => setNewVendor(e.target.value)}>
            <option value="">Choose a vendor…</option>
            {vendors.data.filter((v) => !overridden.has(v.supplier_id)).map((v) => <option key={v.supplier_id} value={v.supplier_id}>{v.name}</option>)}
          </select>
          <Key size="sm" disabled={!newVendor || !q.data} onClick={async () => { await save(q.data!.default, newVendor); setNewVendor(''); }}>Add</Key>
        </div>
      )}
    </Section>
  );
}

function EmailIntake({ admin }: { admin: boolean }) {
  const { toast } = useToast();
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ['email-status'],
    queryFn: () => get<{ running: boolean; configured: boolean; mailbox: string; last_poll: string | null; last_error: string | null; interval_seconds: number; total_invoices_found: number }>('/email/poll-status'),
    refetchInterval: 30_000,
  });
  const run = async (path: string, ok: string) => {
    try {
      await post(path);
      toast(ok);
      qc.invalidateQueries({ queryKey: ['email-status'] });
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Failed', { tone: 'error' });
    }
  };
  const s = q.data;
  return (
    <Section n={3} title="Email intake" lede="Invoices sent to the AP mailbox are picked up automatically.">
      {s && (
        <dl className="kv">
          <dt className="label">Mailbox</dt><dd className="num">{s.mailbox}</dd>
          <dt className="label">State</dt><dd>{!s.configured ? <span className="ink ink--pencil">Not configured</span> : s.running ? <span className="ink ink--ok">Checking every {s.interval_seconds}s</span> : <span className="ink ink--hold">Stopped</span>}</dd>
          <dt className="label">Last check</dt><dd className="num">{s.last_poll ? `${date(s.last_poll)} ${new Date(s.last_poll).toLocaleTimeString('en-GB')}` : '—'}</dd>
          <dt className="label">Found so far</dt><dd className="num">{s.total_invoices_found}</dd>
          {s.last_error && (<><dt className="label">Last error</dt><dd className="ink ink--bad">{s.last_error}</dd></>)}
        </dl>
      )}
      {admin && s?.configured && (
        <div className="tol__actions">
          <Key size="sm" onClick={() => run('/email/poll-now', 'Mailbox checked')}>Check now</Key>
          {s.running
            ? <Key size="sm" variant="ghost" onClick={() => run('/email/poll-stop', 'Email intake stopped')}>Stop</Key>
            : <Key size="sm" variant="primary" onClick={() => run('/email/poll-start', 'Email intake started')}>Start</Key>}
        </div>
      )}
    </Section>
  );
}

function Users({ me }: { me: User }) {
  const qc = useQueryClient();
  const { toast } = useToast();
  const q = useQuery({ queryKey: ['users'], queryFn: () => get<User[]>('/users') });
  const [form, setForm] = useState({ email: '', name: '', role: 'ap_clerk' });
  const [temp, setTemp] = useState<string | null>(null);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const r = await post<{ user: User; temporary_password: string | null }>('/users', form);
      setTemp(r.temporary_password ? `${r.user.email}: ${r.temporary_password}` : null);
      setForm({ email: '', name: '', role: 'ap_clerk' });
      qc.invalidateQueries({ queryKey: ['users'] });
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Could not add user', { tone: 'error' });
    }
  };
  const update = async (u: User, body: Partial<User>) => {
    try {
      await patch(`/users/${u.id}`, body);
      qc.invalidateQueries({ queryKey: ['users'] });
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Could not update', { tone: 'error' });
    }
  };

  return (
    <Section n={4} title="People" lede="Clerks correct and hold; approvers approve and reject; admins change settings.">
      <ol className="ruled-list people">
        {q.data?.map((u) => (
          <li key={u.id}>
            <span><strong>{u.name}</strong> <span className="muted num">{u.email}</span></span>
            <label className="sr-only" htmlFor={`role-${u.id}`}>Role for {u.email}</label>
            <select id={`role-${u.id}`} className="input input--sm" value={u.role} disabled={u.id === me.id} onChange={(e) => update(u, { role: e.target.value as User['role'] })}>
              {(['viewer', 'ap_clerk', 'approver', 'admin'] as const).map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}
            </select>
            <button type="button" className="linkish" disabled={u.id === me.id} onClick={() => update(u, { active: !u.active })}>{u.active ? 'Deactivate' : 'Reactivate'}</button>
          </li>
        ))}
      </ol>
      <form className="inline-form" onSubmit={add}>
        <label className="sr-only" htmlFor="nu-name">Name</label>
        <input id="nu-name" className="input" placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        <label className="sr-only" htmlFor="nu-email">Email</label>
        <input id="nu-email" className="input" type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
        <label className="sr-only" htmlFor="nu-role">Role</label>
        <select id="nu-role" className="input" value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
          {(['viewer', 'ap_clerk', 'approver', 'admin'] as const).map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}
        </select>
        <Key type="submit" size="sm" variant="primary">Add person</Key>
      </form>
      {temp && <Notice>Temporary password for <span className="num">{temp}</span>. Share it privately; it is shown once.</Notice>}
    </Section>
  );
}

function Preferences() {
  const { density, setDensity } = usePrefs();
  return (
    <Section n={5} title="On this device" lede="Stored in this browser only.">
      <div className="pref-row">
        <span className="label">Paper effects</span>
        <FxSwitch />
        <span className="muted small">Full: stamps drop, copies fan out, rows tear off. Subtle: gentle fades. Off: no motion.</span>
      </div>
      <div className="pref-row">
        <span className="label">Row density</span>
        <div className="seg" role="group" aria-label="Row density">
          <button type="button" aria-pressed={density === 'comfortable'} onClick={() => setDensity('comfortable')}>Comfortable</button>
          <button type="button" aria-pressed={density === 'ledger'} onClick={() => setDensity('ledger')}>Ledger</button>
        </div>
      </div>
    </Section>
  );
}

function Demo() {
  const { toast } = useToast();
  const { track } = useRealtime();
  const [busy, setBusy] = useState(false);
  return (
    <Section n={6} title="Demo invoices" lede="Thirteen sample invoices built from real purchase orders, one per matching rule.">
      <Key busy={busy} onClick={async () => {
        setBusy(true);
        try {
          const r = await post<{ accepted: number; items: UploadItem[] }>('/invoices/process-demo');
          track(r.items);
          toast(r.accepted ? `${r.accepted} demo invoices sent to the tray` : 'Demo invoices were already processed');
        } catch (e) {
          toast(e instanceof Error ? e.message : 'Failed', { tone: 'error' });
        } finally {
          setBusy(false);
        }
      }}>Process demo invoices</Key>
    </Section>
  );
}
