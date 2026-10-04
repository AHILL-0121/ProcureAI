export function StampLogo({ size = 40, className = '' }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 80 80" className={`logo ${className}`} aria-hidden="true" style={{ filter: 'url(#ink)' }}>
      <defs>
        <path id="logo-ring" d="M40,40 m-29,0 a29,29 0 1,1 58,0 a29,29 0 1,1 -58,0" />
      </defs>
      <circle cx="40" cy="40" r="37" fill="none" stroke="currentColor" strokeWidth="3" />
      <circle cx="40" cy="40" r="21" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <text fontFamily="var(--f-cond)" fontWeight="700" fontSize="9.4" letterSpacing="2.4" fill="currentColor">
        <textPath href="#logo-ring">PROCUREAI · MATCHED · PROCUREAI ·</textPath>
      </text>
      <path d="M31 41 l6 6 l12 -14" fill="none" stroke="currentColor" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
