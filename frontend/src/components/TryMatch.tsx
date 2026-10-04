'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { MatchLens, VerdictStamp } from '@/components/MatchLens';
import { StatusInk } from '@/components/ui';
import { ISSUE_LABEL, SEVERITY_TONE } from '@/lib/format';
import type { InvoiceDetail } from '@/lib/types';

/** A recorded run of the real pipeline over one of the sample invoices in backend/samples. */
interface DemoRun {
  key: string;
  text: string;
  invoice: InvoiceDetail;
}

const SCENARIOS: Record<string, { title: string; blurb: string }> = {
  '01_full_match': { title: 'A clean one', blurb: 'Billed exactly what was ordered and received.' },
  '06_multiline_full_match': { title: 'Three lines, all agree', blurb: 'Every line ties to the PO and the goods receipt.' },
  '03_price_over_tolerance': { title: 'Price crept up', blurb: 'The unit price is 8% above the purchase order.' },
  '04_qty_exceeds_received': { title: 'Billed for more', blurb: 'Ten more units than the warehouse signed for.' },
  '07_unauthorised_extra_line': { title: 'A surprise surcharge', blurb: 'A freight line nobody ordered.' },
  '12_goods_not_received_ON_HOLD': { title: 'Nothing arrived yet', blurb: 'Invoiced before the goods reached the dock.' },
  '10_vendor_mismatch': { title: 'Wrong supplier', blurb: 'The PO belongs to a different vendor.' },
  '05_unknown_po': { title: 'Mystery PO number', blurb: 'The quoted purchase order is not in the ERP.' },
};

const STEPS = ['Received', 'Read', 'Check', 'Look up', 'Match'];
const STEP_MS = 650;

export function TryMatch({ still }: { still: boolean }) {
  const [runs, setRuns] = useState<DemoRun[] | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [step, setStep] = useState(0);   // 0..STEPS.length; STEPS.length means done
  const timer = useRef<number | undefined>(undefined);
  const stage = useRef<HTMLDivElement>(null);

  useEffect(() => {
    import('@/lib/demo-runs.json').then((m) => setRuns(m.default as unknown as DemoRun[]));
    return () => window.clearInterval(timer.current);
  }, []);

  const run = (key: string) => {
    window.clearInterval(timer.current);
    setPicked(key);
    // On narrow screens the stage sits below the tray; bring it into view
    if (window.matchMedia('(max-width: 900px)').matches) {
      stage.current?.scrollIntoView({ behavior: still ? 'auto' : 'smooth', block: 'start' });
    }
    if (still) {
      setStep(STEPS.length);
      return;
    }
    setStep(0);
    timer.current = window.setInterval(() => {
      setStep((s) => {
        if (s + 1 >= STEPS.length) window.clearInterval(timer.current);
        return s + 1;
      });
    }, STEP_MS);
  };

  const current = runs?.find((r) => r.key === picked) ?? null;
  const done = step >= STEPS.length;
  const inv = current?.invoice;

  return (
    <section className="try" id="try" aria-labelledby="try-title">
      <header className="try__head">
        <p className="label">Try it · no sign-in</p>
        <h2 className="display" id="try-title">Drop an invoice in the tray.</h2>
        <p className="muted">Eight sample invoices, each built from a real purchase order to break (or pass) one rule. Pick one and watch it go through the five stations.</p>
      </header>

      <div className="try__grid">
        <ul className="try__tray" aria-label="Sample invoices">
          {Object.entries(SCENARIOS).map(([key, s]) => (
            <li key={key}>
              <button type="button" className="envelope" aria-pressed={picked === key} disabled={!runs} onClick={() => run(key)}>
                <b>{s.title}</b>
                <span>{s.blurb}</span>
              </button>
            </li>
          ))}
        </ul>

        <div className="try__stage" ref={stage}>
          <ol className="try-rail" aria-label="Pipeline progress">
            {STEPS.map((name, i) => (
              <li key={name} className={`try-rail__stop ${picked && (i < step || done) ? 'is-done' : ''} ${picked && i === step && !done ? 'is-now' : ''}`}>
                <span className="try-rail__hole" aria-hidden />
                {name}
              </li>
            ))}
          </ol>
          <p className="sr-only" aria-live="polite">
            {current ? (done ? `Finished: ${inv?.status.toLowerCase().replace('_', ' ')}` : `${STEPS[step]}…`) : ''}
          </p>

          {!current && <p className="try__empty hand">Pick an invoice from the tray to start.</p>}

          {current && !done && (
            <pre className="try__paper num" aria-label="The invoice as received">{current.text.trimEnd()}</pre>
          )}

          {current && done && inv && (
            <div className="try__result">
              <MatchLens invoice={inv} stacked={false} stamp={<VerdictStamp invoice={inv} drop={!still} />} />
              <div className="try__checks">
                <h3 className="label">What the checker found</h3>
                {(inv.discrepancies ?? []).length === 0 ? (
                  <p className="ink ink--ok">Every check passed. It clears for payment without anyone touching it.</p>
                ) : (
                  <ul className="checks">
                    {(inv.discrepancies ?? []).map((d, i) => (
                      <li key={i} className={`check check--${SEVERITY_TONE[d.severity]}`}>
                        <StatusInk tone={SEVERITY_TONE[d.severity]} label={ISSUE_LABEL[d.type] ?? d.type} />
                        <p>{d.message}</p>
                      </li>
                    ))}
                  </ul>
                )}
                <p className="muted small">
                  {inv.status === 'MATCHED'
                    ? 'Matched invoices skip the in-tray.'
                    : 'This one would wait in the in-tray for a person to approve, hold or reject.'}{' '}
                  A recorded run of the matching engine on demo ERP data. <Link href="/login">Sign in</Link> to match your own.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
