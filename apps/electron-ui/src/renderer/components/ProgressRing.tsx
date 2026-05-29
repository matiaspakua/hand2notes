interface Props {
  percent: number;
  status: string;
  subtitle?: string;
  size?: number;
}

/** Animated circular progress indicator with a gradient stroke. */
export function ProgressRing({ percent, status, subtitle, size = 92 }: Props) {
  const stroke = 8;
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const clamped = Math.max(0, Math.min(100, percent));
  const offset = circumference * (1 - clamped / 100);

  return (
    <div className="h2n-ring-wrap">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`${clamped}% complete`}>
        <defs>
          <linearGradient id="h2n-ring-grad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#6366f1" />
            <stop offset="100%" stopColor="#06b6d4" />
          </linearGradient>
        </defs>
        <circle className="h2n-ring-track" cx={size / 2} cy={size / 2} r={r} fill="none" strokeWidth={stroke} />
        <circle
          className="h2n-ring-fill"
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
        <text className="h2n-ring-label" x="50%" y="50%" dominantBaseline="central" textAnchor="middle">
          {clamped}%
        </text>
      </svg>
      <div>
        <div className="h2n-ring-status">{status}</div>
        {subtitle && <div className="h2n-ring-sub">{subtitle}</div>}
      </div>
    </div>
  );
}
