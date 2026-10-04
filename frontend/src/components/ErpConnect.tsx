'use client';

import { useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { DownloadSimple, FileCsv, X } from '@phosphor-icons/react';
import { Key, Notice } from '@/components/ui';
import { api, get, qs } from '@/lib/api';
import { date, time } from '@/lib/format';
import { useToast } from '@/lib/toast';
import type { ErpImportResult, ErpLayout, ErpStatus } from '@/lib/types';

type Mode = 'merge' | 'replace';

const MODE_TEXT: Record<Mode, string> = {
  merge: 'New rows are added and rows with a known ERP id are updated. Nothing is deleted.',
  replace: 'Every vendor, PO, receipt and material is deleted first, then your files are loaded. Needs vendors, PO headers and PO lines.',
};

const n = (v: number | undefined) => (v ?? 0).toLocaleString('en-GB');

function sendFiles(files: File[], mode: Mode, dryRun: boolean, rematch: boolean) {
  const form = new FormData();
  files.forEach((f) => form.append('files', f, f.name));
  return api<ErpImportResult>(`/erp/import${qs({ mode, dry_run: String(dryRun), rematch: String(rematch) })}`, { method: 'POST', body: form });
}

function downloadTemplate(l: ErpLayout) {
  const blob = new Blob([[...l.required, ...l.optional].join(',') + '\n'], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = l.file;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

/** Settings section: what ERP data is loaded, and (admins) a checked, all-or-nothing CSV import. */
export function ErpConnect({ admin }: { admin: boolean }) {
  const q = useQuery({ queryKey: ['erp-status'], queryFn: () => get<ErpStatus>('/erp/status') });
  const s = q.data;
  return (
    <>
      {q.isError && <Notice tone="bad">{(q.error as Error).message}</Notice>}
      {s && <ErpState status={s} />}
      {admin && s && <ErpImport layouts={s.layouts} />}
      {s && (
        <details className="erp-layouts">
          <summary className="linkish">CSV layouts and templates</summary>
          <p className="muted small">Export these from your ERP. Files are recognised by name or by their header row; <b>bold</b> columns are required. Dates as YYYY-MM-DD; commas or semicolons both work.</p>
          <ol className="ruled-list">
            {s.layouts.map((l) => (
              <li key={l.name}>
                <span className="erp-layouts__cols">
                  <strong>{l.label}</strong> <span className="num muted">{l.file}</span>
                  <span className="num small">{l.required.map((c) => <b key={c}>{c} </b>)}{l.optional.map((c) => <span key={c} className="muted">{c} </span>)}</span>
                </span>
                <button type="button" className="linkish" onClick={() => downloadTemplate(l)}><DownloadSimple aria-hidden /> Template</button>
              </li>
            ))}
          </ol>
        </details>
      )}
    </>
  );
}

function ErpState({ status: s }: { status: ErpStatus }) {
  const cells: [string, string][] = [
    ['vendors', 'Vendors'], ['materials', 'Materials'], ['po_headers', 'Purchase orders'], ['po_lines', 'PO lines'],
    ['goods_receipts', 'Goods receipts'], ['invoices', 'Invoice history'],
  ];
  const li = s.last_import;
  return (
    <>
      {s.source === 'empty' && <Notice tone="hold">No ERP data yet. Invoices can’t be matched until purchase orders are loaded.</Notice>}
      <dl className="kv">
        <dt className="label">Source</dt>
        <dd>
          {s.source === 'import' && li && (<>File import · <span className="num">{date(li.at)} {time(li.at)}</span> by {li.by} · {li.mode === 'replace' ? 'replaced all' : 'added & updated'}</>)}
          {s.source === 'sample' && <>Sample dataset shipped with ProcureAI. Import your own files below to replace it.</>}
          {s.source === 'empty' && <span className="ink ink--pencil">Nothing loaded</span>}
        </dd>
        {li && li.files.length > 0 && (<><dt className="label">Files</dt><dd className="num small">{li.files.join(' · ')}</dd></>)}
      </dl>
      <div className="erp-tally" role="list" aria-label="ERP records loaded">
        {cells.map(([k, label]) => (
          <div key={k} role="listitem"><span className="label">{label}</span><b className="num">{n(s.counts[k])}</b></div>
        ))}
      </div>
    </>
  );
}

function ErpImport({ layouts }: { layouts: ErpLayout[] }) {
  const qc = useQueryClient();
  const { toast } = useToast();
  const input = useRef<HTMLInputElement>(null);
  const [mode, setMode] = useState<Mode>('merge');
  const [files, setFiles] = useState<File[]>([]);
  const [report, setReport] = useState<ErpImportResult | null>(null);
  const [busy, setBusy] = useState<'check' | 'import' | null>(null);
  const [over, setOver] = useState(false);
  const [rematch, setRematch] = useState(true);
  const [confirmReplace, setConfirmReplace] = useState(false);

  const reset = () => { setReport(null); setConfirmReplace(false); };
  const addFiles = (list: FileList | File[]) => {
    const csv = Array.from(list).filter((f) => /\.(csv|txt)$/i.test(f.name) || f.type === 'text/csv');
    const skipped = Array.from(list).length - csv.length;
    if (skipped) toast(`${skipped} file${skipped > 1 ? 's' : ''} skipped: only CSV files can be imported`, { tone: 'error' });
    setFiles((prev) => [...prev.filter((p) => !csv.some((c) => c.name === p.name)), ...csv].slice(0, layouts.length));
    reset();
  };

  const run = async (dryRun: boolean) => {
    setBusy(dryRun ? 'check' : 'import');
    try {
      const r = await sendFiles(files, mode, dryRun, rematch);
      if (r.committed) {
        const rows = Object.values(r.counts ?? {}).reduce((a, b) => a + b, 0);
        toast(`${n(rows)} ERP rows imported${r.rematching ? `. Re-checking ${r.rematching} waiting invoice${r.rematching > 1 ? 's' : ''}` : ''}`);
        setFiles([]);
        reset();
        ['erp-status', 'health', 'pos', 'po', 'vendors', 'tolerances', 'invoices', 'invoice', 'stats'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
      } else {
        setReport(r);
      }
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Import failed', { tone: 'error' });
    } finally {
      setBusy(null);
    }
  };

  const errorCount = report ? report.entities.reduce((a, e) => a + e.error_count, 0) + report.problems.length : 0;
  const canImport = !!report?.ok && (mode === 'merge' || confirmReplace);

  return (
    <div className="erp-import">
      <p className="tol__title">Import from your ERP</p>
      <div className="pref-row">
        <span className="label">Mode</span>
        <div className="seg" role="group" aria-label="Import mode">
          <button type="button" aria-pressed={mode === 'merge'} onClick={() => { setMode('merge'); reset(); }}>Add &amp; update</button>
          <button type="button" aria-pressed={mode === 'replace'} onClick={() => { setMode('replace'); reset(); }}>Replace all</button>
        </div>
        <span className="muted small">{MODE_TEXT[mode]}</span>
      </div>

      <div
        data-own-drop
        className={`erp-drop ${over ? 'is-over' : ''}`}
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); addFiles(e.dataTransfer.files); }}
      >
        <FileCsv size={26} aria-hidden />
        <span>Drop CSV exports here, or <button type="button" className="linkish" onClick={() => input.current?.click()}>choose files</button></span>
        <span className="label">Up to {layouts.length} files · one per layout</span>
        <input ref={input} id="erp-files" type="file" accept=".csv,text/csv" multiple hidden onChange={(e) => { if (e.target.files) addFiles(e.target.files); e.target.value = ''; }} />
      </div>

      {files.length > 0 && (
        <ul className="erp-files">
          {files.map((f) => (
            <li key={f.name}>
              <span className="num">{f.name}</span>
              <span className="muted small">{(f.size / 1024).toFixed(0)} KB</span>
              <button type="button" className="icon-btn" aria-label={`Remove ${f.name}`} onClick={() => { setFiles(files.filter((x) => x !== f)); reset(); }}><X aria-hidden /></button>
            </li>
          ))}
        </ul>
      )}

      {report && <ErpReport report={report} />}

      {report?.ok && (
        <div className="erp-confirm">
          <label className="erp-check">
            <input type="checkbox" checked={rematch} onChange={(e) => setRematch(e.target.checked)} />
            <span>Re-check invoices waiting in the in-tray or on hold against the new data</span>
          </label>
          {mode === 'replace' && (
            <label className="erp-check erp-check--bad">
              <input type="checkbox" checked={confirmReplace} onChange={(e) => setConfirmReplace(e.target.checked)} />
              <span>I understand the current vendors, POs, receipts and materials will be deleted</span>
            </label>
          )}
        </div>
      )}

      <div className="tol__actions">
        {files.length > 0 && <Key size="sm" variant="ghost" onClick={() => { setFiles([]); reset(); }}>Clear</Key>}
        <Key size="sm" disabled={!files.length} busy={busy === 'check'} onClick={() => run(true)}>{report ? 'Check again' : 'Check files'}</Key>
        <Key size="sm" variant={mode === 'replace' ? 'danger' : 'primary'} disabled={!canImport} busy={busy === 'import'} onClick={() => run(false)}>
          {mode === 'replace' ? 'Replace ERP data' : 'Import'}
        </Key>
      </div>
      {report && !report.ok && <p className="field-error">{n(errorCount)} problem{errorCount === 1 ? '' : 's'} to fix. Nothing has been imported; correct the files and check again.</p>}
    </div>
  );
}

function ErpReport({ report }: { report: ErpImportResult }) {
  const withErrors = report.entities.filter((e) => e.errors.length);
  return (
    <div className="erp-report">
      {report.problems.map((p) => <Notice key={p} tone="bad">{p}</Notice>)}
      {report.warnings.map((w) => <Notice key={w} tone="hold">{w}</Notice>)}
      <div className="erp-report__scroll">
        <table>
          <thead>
            <tr><th>Layout</th><th>File</th><th className="r">Rows</th><th className="r">New</th><th className="r">Updated</th><th className="r">Problems</th></tr>
          </thead>
          <tbody>
            {report.entities.map((e) => (
              <tr key={e.name}>
                <td>{e.label}</td>
                <td className="num">{e.filename ?? <span className="ink ink--hold">will be emptied</span>}</td>
                <td className="num r">{n(e.rows)}</td>
                <td className="num r">{report.ok ? n(e.inserts) : '—'}</td>
                <td className="num r">{report.ok ? n(e.updates) : '—'}</td>
                <td className="num r">{e.error_count ? <span className="ink ink--bad">{n(e.error_count)}</span> : <span className="ink ink--ok">0</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {withErrors.map((e) => (
        <div key={e.name} className="erp-errors">
          <p className="label">{e.filename}{e.error_count > e.errors.length && ` · first ${e.errors.length} of ${n(e.error_count)}`}</p>
          <ol>
            {e.errors.map((x, i) => (
              <li key={i}><span className="num">row {x.row ?? '—'}{x.column && ` · ${x.column}`}</span> {x.message}</li>
            ))}
          </ol>
        </div>
      ))}
    </div>
  );
}
