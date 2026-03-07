'use client';

import { useState, useEffect, useRef, ReactNode } from 'react';
import { tokens, statusColors } from '@/lib/design-tokens';

// ─── PERCY MASCOT ─────────────────────────────────────────────────────────────
interface PercyMascotProps {
  size?: number;
  mood?: 'happy' | 'thinking' | 'excited' | 'worried';
  animate?: boolean;
}

export function PercyMascot({ size = 120, mood = 'happy', animate = true }: PercyMascotProps) {
  const [blink, setBlink] = useState(false);
  const [bobOffset, setBobOffset] = useState(0);

  useEffect(() => {
    if (!animate) return;
    const blinkInterval = setInterval(() => {
      setBlink(true);
      setTimeout(() => setBlink(false), 150);
    }, 3200);
    let t = 0;
    const bob = setInterval(() => {
      t += 0.06;
      setBobOffset(Math.sin(t) * 5);
    }, 16);
    return () => { clearInterval(blinkInterval); clearInterval(bob); };
  }, [animate]);

  const moods = {
    happy: { mouth: "M 38 68 Q 50 78 62 68", eyebrow: "normal", blush: true },
    thinking: { mouth: "M 40 70 Q 50 70 60 70", eyebrow: "raised", blush: false },
    excited: { mouth: "M 35 66 Q 50 80 65 66", eyebrow: "raised", blush: true },
    worried: { mouth: "M 38 72 Q 50 65 62 72", eyebrow: "worried", blush: false },
  };
  const m = moods[mood] || moods.happy;

  return (
    <svg
      width={size} height={size * 1.3}
      viewBox="0 0 100 130"
      style={{ transform: `translateY(${bobOffset}px)`, transition: "transform 0.05s", overflow: "visible" }}
    >
      <ellipse cx="50" cy="128" rx="28" ry="5" fill="#00000018" />
      <rect x="18" y="10" width="64" height="82" rx="8" fill="#FFFDF7"
        stroke={tokens.ember} strokeWidth="2.5" filter="url(#shadow)" />
      <path d="M 66 10 L 82 26 L 66 26 Z" fill={tokens.sand} stroke={tokens.ember} strokeWidth="1.5" />
      {[38, 44, 50, 56, 62].map((y, i) => (
        <rect key={i} x="26" y={y} width={i === 0 ? 36 : i === 1 ? 28 : 22} height="2.5"
          rx="1.5" fill={i < 2 ? tokens.ember + "60" : tokens.mist + "90"} />
      ))}
      <rect x="50" y="38" width="14" height="2.5" rx="1.5" fill={tokens.forest + "80"} />
      <circle cx="50" cy="52" r="22" fill={tokens.parchment} />
      <ellipse cx="42" cy="49" rx="4" ry={blink ? 0.5 : 4.5} fill={tokens.charcoal}
        style={{ transition: "ry 0.08s" }} />
      <ellipse cx="58" cy="49" rx="4" ry={blink ? 0.5 : 4.5} fill={tokens.charcoal}
        style={{ transition: "ry 0.08s" }} />
      {!blink && <>
        <circle cx="44" cy="47" r="1.5" fill="white" />
        <circle cx="60" cy="47" r="1.5" fill="white" />
      </>}
      {m.eyebrow === "raised" && <>
        <path d="M 38 42 Q 42 39 46 42" stroke={tokens.charcoal} strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M 54 42 Q 58 39 62 42" stroke={tokens.charcoal} strokeWidth="2" fill="none" strokeLinecap="round" />
      </>}
      {m.eyebrow === "normal" && <>
        <path d="M 38 43 Q 42 41 46 43" stroke={tokens.charcoal} strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M 54 43 Q 58 41 62 43" stroke={tokens.charcoal} strokeWidth="2" fill="none" strokeLinecap="round" />
      </>}
      {m.eyebrow === "worried" && <>
        <path d="M 38 43 Q 42 45 46 43" stroke={tokens.charcoal} strokeWidth="2" fill="none" strokeLinecap="round" />
        <path d="M 54 43 Q 58 45 62 43" stroke={tokens.charcoal} strokeWidth="2" fill="none" strokeLinecap="round" />
      </>}
      {m.blush && <>
        <ellipse cx="36" cy="55" rx="5" ry="3" fill={tokens.coral + "50"} />
        <ellipse cx="64" cy="55" rx="5" ry="3" fill={tokens.coral + "50"} />
      </>}
      <path d={m.mouth} stroke={tokens.charcoal} strokeWidth="2.5"
        fill="none" strokeLinecap="round" />
      <path d="M 18 60 Q 8 55 10 68" stroke={tokens.amber} strokeWidth="4"
        fill="none" strokeLinecap="round" />
      <path d="M 82 60 Q 92 55 90 68" stroke={tokens.amber} strokeWidth="4"
        fill="none" strokeLinecap="round" />
      <circle cx="10" cy="68" r="4" fill={tokens.gold} />
      <circle cx="90" cy="68" r="4" fill={tokens.gold} />
      <circle cx="69" cy="80" r="9" fill={tokens.forest} />
      <text x="69" y="84" textAnchor="middle" fontSize="8" fill="white" fontWeight="bold">✓</text>
      <defs>
        <filter id="shadow">
          <feDropShadow dx="2" dy="4" stdDeviation="3" floodColor="#00000030" />
        </filter>
      </defs>
    </svg>
  );
}

// ─── 3D TILT CARD ─────────────────────────────────────────────────────────────
interface TiltCardProps {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

export function TiltCard({ children, className = "", style = {} }: TiltCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const handleMove = (e: React.MouseEvent) => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    ref.current.style.transform = `perspective(600px) rotateY(${x * 14}deg) rotateX(${-y * 14}deg) scale(1.03)`;
  };
  const reset = () => {
    if (!ref.current) return;
    ref.current.style.transform = "perspective(600px) rotateY(0deg) rotateX(0deg) scale(1)";
  };
  return (
    <div ref={ref} onMouseMove={handleMove} onMouseLeave={reset}
      className={className}
      style={{ transition: "transform 0.15s ease-out", ...style }}>
      {children}
    </div>
  );
}

// ─── ANIMATED COUNTER ─────────────────────────────────────────────────────────
interface AnimCounterProps {
  to: number;
  prefix?: string;
  suffix?: string;
  duration?: number;
}

export function AnimCounter({ to, prefix = "", suffix = "", duration = 1600 }: AnimCounterProps) {
  const [val, setVal] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      obs.disconnect();
      const start = performance.now();
      const tick = (now: number) => {
        const p = Math.min((now - start) / duration, 1);
        const ease = 1 - Math.pow(1 - p, 3);
        setVal(Math.round(ease * to));
        if (p < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }, { threshold: 0.5 });
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, [to, duration]);

  return <span ref={ref}>{prefix}{val.toLocaleString()}{suffix}</span>;
}

// ─── SMOOTH SKELETON LOADER ───────────────────────────────────────────────────
interface SkeletonProps {
  w?: string | number;
  h?: number;
  r?: number;
  style?: React.CSSProperties;
}

export function Skeleton({ w = "100%", h = 20, r = 8, style = {} }: SkeletonProps) {
  return (
    <div style={{
      width: w, height: h, borderRadius: r,
      background: `linear-gradient(90deg, ${tokens.sand}80 0%, ${tokens.parchment} 50%, ${tokens.sand}80 100%)`,
      backgroundSize: "200% 100%",
      animation: "shimmer 1.6s infinite linear",
      ...style
    }} />
  );
}

// ─── STATUS BADGE ─────────────────────────────────────────────────────────────
interface BadgeProps {
  type: string;
}

export function Badge({ type }: BadgeProps) {
  const s = statusColors[type as keyof typeof statusColors] || statusColors.PROCESSING;
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 6, padding: "4px 12px",
      background: s.bg, color: s.color, borderRadius: 999, fontSize: 12, fontWeight: 700,
      letterSpacing: "0.03em",
    }}>
      <span style={{
        width: 7, height: 7, borderRadius: "50%", background: s.dot,
        boxShadow: type === "FULL_MATCH" || type === "MATCHED" ? `0 0 6px ${s.dot}` : "none",
        animation: type === "PROCESSING" || type === "EXTRACTING" ? "pulse 1s infinite" : "none",
      }} />
      {s.label}
    </span>
  );
}

// ─── ENTRANCE REVEAL ──────────────────────────────────────────────────────────
interface RevealProps {
  children: ReactNode;
  delay?: number;
  direction?: 'up' | 'left' | 'right' | 'scale';
}

export function Reveal({ children, delay = 0, direction = "up" }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [vis, setVis] = useState(false);
  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setVis(true); obs.disconnect(); }
    }, { threshold: 0.15 });
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, []);
  const from = { up: "translateY(40px)", left: "translateX(-40px)", right: "translateX(40px)", scale: "scale(0.92)" };
  return (
    <div ref={ref} style={{
      opacity: vis ? 1 : 0,
      transform: vis ? "none" : from[direction] || from.up,
      transition: `opacity 0.7s ease ${delay}ms, transform 0.7s cubic-bezier(0.16,1,0.3,1) ${delay}ms`,
    }}>
      {children}
    </div>
  );
}

// ─── AGENT PIPELINE STEP ──────────────────────────────────────────────────────
interface AgentStepProps {
  icon: string;
  label: string;
  sublabel: string;
  active?: boolean;
  done?: boolean;
  delay?: number;
}

export function AgentStep({ icon, label, sublabel, active, done, delay = 0 }: AgentStepProps) {
  return (
    <Reveal delay={delay} direction="left">
      <div style={{
        display: "flex", alignItems: "center", gap: 14,
        padding: "14px 18px", borderRadius: 14,
        background: done ? `${tokens.forest}12` : active ? `${tokens.amber}14` : `${tokens.sand}50`,
        border: `1.5px solid ${done ? tokens.forest + "40" : active ? tokens.amber + "60" : tokens.sand}`,
        transition: "all 0.4s ease", cursor: "default",
      }}>
        <div style={{
          width: 40, height: 40, borderRadius: 12,
          background: done ? tokens.forest : active ? tokens.amber : tokens.sand,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 20, flexShrink: 0,
          boxShadow: done ? `0 0 14px ${tokens.forest}50` : active ? `0 0 14px ${tokens.amber}60` : "none",
          transition: "all 0.4s ease",
        }}>
          {done ? "✓" : icon}
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: 13, color: tokens.charcoal }}>{label}</div>
          <div style={{ fontSize: 11, color: tokens.mist }}>{sublabel}</div>
        </div>
        {active && (
          <div style={{ marginLeft: "auto", display: "flex", gap: 3 }}>
            {[0, 1, 2].map(i => (
              <div key={i} style={{
                width: 5, height: 5, borderRadius: "50%", background: tokens.amber,
                animation: `bounce 0.8s ${i * 0.15}s infinite`,
              }} />
            ))}
          </div>
        )}
      </div>
    </Reveal>
  );
}
