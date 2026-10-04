'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { motion, useReducedMotion, useScroll, useSpring, useTransform } from 'motion/react';
import { StampLogo } from '@/components/Logo';
import { TryMatch } from '@/components/TryMatch';
import { usePrefs } from '@/lib/prefs';
import { wakeServer } from '@/lib/wake';

const STATIONS = [
  { name: 'Received', clerk: 'Opened the post, sorted invoices into a tray.', robot: 'Uploads and the AP mailbox land in one in-tray. The same file twice is recognised by its fingerprint.' },
  { name: 'Read', clerk: 'Typed every field into the ledger by hand.', robot: 'Text PDFs are read directly; scans go through OCR, and a language model fills a strict form. Every guess is noted.' },
  { name: 'Check', clerk: 'Checked the arithmetic and the vendor file.', robot: 'Line maths, tax, currency, vendor master, and a duplicate check that survives restarts.' },
  { name: 'Look up', clerk: 'Pulled the canary PO copy and the pink receiving slip.', robot: 'The purchase order, every receipt against it, and what has already been billed.' },
  { name: 'Match', clerk: 'Ran a finger down three sheets and stamped the result.', robot: 'Line by line: price, received quantity, cumulative billing, vendor, currency. Clean ones clear; the rest go to a person.' },
];

export default function Landing() {
  const hero = useRef<HTMLDivElement>(null);
  const { fx } = usePrefs();
  const reduced = useReducedMotion();
  const still = fx === 'off' || !!reduced;
  const { scrollYProgress } = useScroll({ target: hero, offset: ['start start', 'end start'] });
  const p = useSpring(scrollYProgress, { stiffness: 120, damping: 24, mass: 0.4 });

  // three loose sheets drift into alignment as you scroll; the stamp comes down at the end
  const deskY = useTransform(p, [0, 1], [0, 90]);
  const invX = useTransform(p, [0, 0.6], [-120, 0]);
  const invR = useTransform(p, [0, 0.6], [-9, -1]);
  const poX = useTransform(p, [0, 0.6], [150, 14]);
  const poY = useTransform(p, [0, 0.6], [-40, 10]);
  const poR = useTransform(p, [0, 0.6], [11, 1.5]);
  const grnX = useTransform(p, [0, 0.6], [60, 28]);
  const grnY = useTransform(p, [0, 0.6], [110, 20]);
  const grnR = useTransform(p, [0, 0.6], [-4, 3]);
  const stampY = useTransform(p, [0.55, 0.78], [-260, 0]);
  const stampS = useTransform(p, [0.55, 0.78], [1.7, 1]);
  const stampO = useTransform(p, [0.55, 0.62], [0, 1]);

  // Start booting the (free-tier, sleeping) backend now, so it is up by the time the visitor signs in
  useEffect(() => {
    void wakeServer();
  }, []);

  const [lenisReady, setLenisReady] = useState(false);
  useEffect(() => {
    if (still) return;
    let raf = 0;
    let lenis: { raf: (t: number) => void; destroy: () => void } | null = null;
    import('lenis').then(({ default: Lenis }) => {
      lenis = new Lenis({ lerp: 0.12 });
      const loop = (t: number) => { lenis?.raf(t); raf = requestAnimationFrame(loop); };
      raf = requestAnimationFrame(loop);
      setLenisReady(true);
    });
    return () => { cancelAnimationFrame(raf); lenis?.destroy(); };
  }, [still]);

  const m = (v: unknown) => (still ? undefined : v);

  return (
    <div className="landing" data-lenis={lenisReady || undefined}>
      <header className="landing__nav">
        <Link href="/" className="brand"><StampLogo size={36} /><b className="display">ProcureAI</b></Link>
        <Link href="/login" className="key key--plain key--sm">Sign in</Link>
      </header>

      <section className="hero" ref={hero}>
        <div className="hero__sticky">
          <div className="hero__copy">
            <p className="label">Three-way invoice matching</p>
            <h1 className="display hero__title">Three copies.<br />One stamp.<br />Zero chasing.</h1>
            <p className="hero__lede">
              ProcureAI reads every supplier invoice, lays it beside the purchase order and the goods receipt, and
              stamps the ones that agree. The ones that don&apos;t land in your in-tray, circled in red pencil.
            </p>
            <div className="hero__cta">
              <Link href="/login" className="key key--primary">Open the in-tray</Link>
              <a href="#try" className="key key--plain">Try a sample invoice</a>
              <span className="muted small">or scroll to watch a match</span>
            </div>
          </div>

          <motion.div className="desk" style={{ y: m(deskY) as never }} aria-hidden>
            <motion.div className="loose loose--pink" style={{ x: m(grnX) as never, y: m(grnY) as never, rotate: m(grnR) as never }}>
              <span className="label">Receiving copy</span>
              <i /><i /><i className="short" />
              <b className="num">38 KG ✓</b>
            </motion.div>
            <motion.div className="loose loose--canary" style={{ x: m(poX) as never, y: m(poY) as never, rotate: m(poR) as never }}>
              <span className="label">Purchase order</span>
              <i /><i className="short" /><i />
              <b className="num">PO-000822</b>
            </motion.div>
            <motion.div className="loose loose--white" style={{ x: m(invX) as never, rotate: m(invR) as never }}>
              <span className="label">Invoice</span>
              <strong className="display">Supplier_5</strong>
              <i /><i /><i className="short" /><i />
              <b className="num">INR 7,512.20</b>
              <motion.div className="stamp stamp--ok loose__stamp" style={{ y: m(stampY) as never, scale: m(stampS) as never, opacity: still ? 1 : (stampO as never) }}>
                Matched<small>AUTO · 3-WAY</small>
              </motion.div>
            </motion.div>
          </motion.div>
        </div>
      </section>

      <section className="story">
        <header className="story__head">
          <p className="label">Five stations</p>
          <h2 className="display">How a clerk did it, and how ProcureAI does it.</h2>
        </header>
        <ol className="stations">
          {STATIONS.map((s, i) => (
            <motion.li
              key={s.name}
              className="station"
              initial={still ? false : { opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ duration: 0.5, delay: i * 0.06 }}
            >
              <span className="station__hole" aria-hidden />
              <div className="flip" tabIndex={0}>
                <div className="flip__inner">
                  <div className="flip__face">
                    <span className="label">Station {i + 1} · by hand</span>
                    <h3 className="display">{s.name}</h3>
                    <p className="hand">{s.clerk}</p>
                  </div>
                  <div className="flip__face flip__face--back">
                    <span className="label">Station {i + 1} · ProcureAI</span>
                    <h3 className="display">{s.name}</h3>
                    <p>{s.robot}</p>
                  </div>
                </div>
              </div>
            </motion.li>
          ))}
        </ol>
        <p className="muted small story__hint">Hover or focus a card to turn it over.</p>
      </section>

      <TryMatch still={still} />

      <section className="proof">
        <div className="tape tape--wide" aria-label="What the matching engine checks">
          <div className="tape__ln" style={{ ['--i' as string]: 0 }}><span>UNIT PRICE VS PO</span><span className="tape__dots" /><span>±5% · MIN 0.05</span></div>
          <div className="tape__ln" style={{ ['--i' as string]: 1 }}><span>QTY VS RECEIVED − BILLED</span><span className="tape__dots" /><span>±2%</span></div>
          <div className="tape__ln" style={{ ['--i' as string]: 2 }}><span>VENDOR · CURRENCY · PO OPEN</span><span className="tape__dots" /><span>EXACT</span></div>
          <div className="tape__ln" style={{ ['--i' as string]: 3 }}><span>DUPLICATES</span><span className="tape__dots" /><span>BLOCKED</span></div>
          <div className="tape__rule" />
          <div className="tape__ln tape__tot" style={{ ['--i' as string]: 4 }}><span>SCENARIOS UNDER TEST</span><span>13</span></div>
        </div>
        <div className="proof__copy">
          <h2 className="display">Every verdict shows its working.</h2>
          <p>Open any invoice and the three copies fan out across the desk, lined up by matched line. The number that broke the rule is circled; the tolerance it broke is written underneath.</p>
          <Link href="/login" className="key key--primary">Open the in-tray</Link>
        </div>
      </section>

      <footer className="landing__foot muted small">
        <span>ProcureAI · three-way matching for accounts payable</span>
      </footer>
    </div>
  );
}
