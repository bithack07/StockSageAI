/** Ambient animated backdrop — pure CSS, respects reduced motion. */
export function AnimatedBackground({ variant = 'app' }: { variant?: 'app' | 'login' }) {
  return (
    <div className={`ambient-bg ambient-bg--${variant}`} aria-hidden>
      <div className="ambient-grid" />
      <div className="ambient-orb ambient-orb--1" />
      <div className="ambient-orb ambient-orb--2" />
      <div className="ambient-orb ambient-orb--3" />
      <svg className="ambient-chart" viewBox="0 0 400 120" preserveAspectRatio="none">
        <path className="ambient-chart-line ambient-chart-line--1" d="M0,80 Q50,40 100,55 T200,30 T300,50 T400,20" />
        <path className="ambient-chart-line ambient-chart-line--2" d="M0,95 Q80,70 160,75 T320,45 T400,60" />
      </svg>
      <div className="ambient-particles">
        {Array.from({ length: 12 }).map((_, i) => (
          <span key={i} className="ambient-particle" style={{ '--i': i } as React.CSSProperties} />
        ))}
      </div>
    </div>
  );
}
