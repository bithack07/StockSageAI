/** SVG hero — trading dashboard motif for login & dashboard. */
export function MarketHeroIllustration({ className = '' }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 480 360"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Market analytics illustration"
    >
      <defs>
        <linearGradient id="heroGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#4F8EF7" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#6366F1" stopOpacity="0.08" />
        </linearGradient>
        <linearGradient id="candleUp" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#10B981" />
          <stop offset="100%" stopColor="#059669" />
        </linearGradient>
        <linearGradient id="candleDown" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#F43F5E" />
          <stop offset="100%" stopColor="#E11D48" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="8" result="blur" />
          <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>

      <rect x="40" y="40" width="400" height="280" rx="20" fill="url(#heroGrad)" stroke="#1E2D4A" strokeWidth="1.5" />
      <rect x="40" y="40" width="400" height="48" rx="20" fill="#0D1526" fillOpacity="0.6" />
      <circle cx="68" cy="64" r="6" fill="#F43F5E" opacity="0.8" />
      <circle cx="88" cy="64" r="6" fill="#F59E0B" opacity="0.8" />
      <circle cx="108" cy="64" r="6" fill="#10B981" opacity="0.8" />
      <text x="130" y="70" fill="#8BA3CC" fontSize="13" fontFamily="Inter, sans-serif" fontWeight="600">StockSage · Live Analysis</text>

      {/* Chart grid */}
      {[0, 1, 2, 3, 4].map((i) => (
        <line key={i} x1="60" y1={110 + i * 40} x2="420" y2={110 + i * 40} stroke="#1E2D4A" strokeWidth="1" />
      ))}

      {/* Trend line */}
      <path
        d="M70 250 L120 210 L170 220 L220 170 L270 185 L320 130 L370 145 L410 100"
        stroke="#4F8EF7"
        strokeWidth="2.5"
        strokeLinecap="round"
        filter="url(#glow)"
        className="hero-trend-line"
      />

      {/* Candles */}
      {[
        [90, 200, 12, 45, true], [115, 185, 10, 38, false], [140, 195, 11, 42, true],
        [165, 175, 12, 50, true], [190, 190, 10, 35, false], [215, 160, 13, 55, true],
        [240, 170, 11, 40, false], [265, 145, 12, 48, true], [290, 155, 10, 36, false],
        [315, 125, 13, 52, true], [340, 140, 11, 38, true], [365, 115, 12, 45, true],
      ].map(([x, y, w, h, up], i) => (
        <g key={i}>
          <line x1={x as number} y1={(y as number) - 15} x2={x as number} y2={(y as number) + (h as number) + 10} stroke={up ? '#10B981' : '#F43F5E'} strokeWidth="2" opacity="0.6" />
          <rect x={(x as number) - (w as number) / 2} y={y as number} width={w as number} height={h as number} rx="2" fill={up ? 'url(#candleUp)' : 'url(#candleDown)'} />
        </g>
      ))}

      {/* Agent nodes */}
      <g className="hero-agent-node">
        <rect x="72" y="288" width="88" height="24" rx="8" fill="#111E35" stroke="#4F8EF7" strokeWidth="1" />
        <text x="86" y="304" fill="#4F8EF7" fontSize="10" fontWeight="700" fontFamily="Inter">Fundamental</text>
      </g>
      <g className="hero-agent-node hero-agent-node--delay">
        <rect x="172" y="288" width="72" height="24" rx="8" fill="#111E35" stroke="#10B981" strokeWidth="1" />
        <text x="186" y="304" fill="#10B981" fontSize="10" fontWeight="700" fontFamily="Inter">Technical</text>
      </g>
      <g className="hero-agent-node hero-agent-node--delay2">
        <rect x="256" y="288" width="68" height="24" rx="8" fill="#111E35" stroke="#F59E0B" strokeWidth="1" />
        <text x="268" y="304" fill="#F59E0B" fontSize="10" fontWeight="700" fontFamily="Inter">Sentiment</text>
      </g>
      <g className="hero-agent-node hero-agent-node--delay3">
        <rect x="336" y="288" width="36" height="24" rx="8" fill="#111E35" stroke="#6366F1" strokeWidth="1" />
        <text x="348" y="304" fill="#6366F1" fontSize="10" fontWeight="700" fontFamily="Inter">ML</text>
      </g>

      {/* Floating badge */}
      <rect x="320" y="72" width="100" height="36" rx="10" fill="#111E35" stroke="#10B981" strokeWidth="1" className="hero-float-badge" />
      <text x="338" y="88" fill="#10B981" fontSize="11" fontWeight="800" fontFamily="Inter">BULLISH</text>
      <text x="338" y="102" fill="#8BA3CC" fontSize="9" fontFamily="Inter">AI Confidence 78%</text>
    </svg>
  );
}
