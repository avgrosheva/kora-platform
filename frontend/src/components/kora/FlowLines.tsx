/**
 * Decorative light-trail backdrop. Purely presentational; place as the first
 * child of a \`relative\` scroll container and keep page content at z-10+.
 */
const PATHS = [
  { d: 'M-100,10 C300,10 420,150 600,150 C780,150 900,300 1300,300', dash: '420 900', dur: '11s', delay: '0s', w: 1 },
  { d: 'M-100,80 C260,80 400,190 600,190 C820,190 940,60 1300,60',   dash: '300 1000', dur: '14s', delay: '2.5s', w: 1 },
  { d: 'M-100,240 C320,240 430,120 600,120 C790,120 880,240 1300,240', dash: '360 1000', dur: '17s', delay: '6s', w: 1 },
  { d: 'M-100,350 C340,350 470,220 620,220 C800,220 960,350 1300,350', dash: '240 1100', dur: '20s', delay: '9s', w: 0.8 },
];

export function FlowLines({ height = 420 }: { height?: number }) {
  return (
    <svg
      viewBox="0 0 1200 420"
      preserveAspectRatio="none"
      aria-hidden="true"
      className="pointer-events-none absolute inset-x-0 top-0 w-full opacity-75"
      style={{ height }}
    >
      <defs>
        <linearGradient id="kora-line" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#4D8DFF" stopOpacity="0" />
          <stop offset="45%" stopColor="#6FA8FF" stopOpacity="0.9" />
          <stop offset="100%" stopColor="#4D8DFF" stopOpacity="0" />
        </linearGradient>
        <radialGradient id="kora-halo" cx="50%" cy="0%" r="70%">
          <stop offset="0%" stopColor="#1D4C9E" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#05070A" stopOpacity="0" />
        </radialGradient>
      </defs>
      <rect x="0" y="0" width="1200" height="420" fill="url(#kora-halo)" />
      {PATHS.map((p) => (
        <path
          key={p.d}
          d={p.d}
          fill="none"
          stroke="url(#kora-line)"
          strokeWidth={p.w}
          strokeDasharray={p.dash}
          className="kora-flow"
          style={{ animationDuration: p.dur, animationDelay: p.delay }}
        />
      ))}
    </svg>
  );
}
