type StatRowProps = {
  label: string
  home: number
  away: number
  fmt?: 'int' | 'float' | 'pct'
}

export default function StatRow({ label, home, away, fmt = 'int' }: StatRowProps) {
  const fmtVal = (value: number) => {
    if (fmt === 'pct') return `${Math.round(value)}%`
    if (fmt === 'float') return value.toFixed(2)
    return String(Math.round(value))
  }
  const total = home + away
  const homePct = total > 0 ? (home / total) * 100 : 50
  const homeBar = homePct < 10 ? 10 : homePct > 90 ? 90 : homePct
  const awayBar = 100 - homeBar

  return (
    <div>
      <div className="d-flex justify-content-between small mb-1">
        <span className="fw-semibold">{fmtVal(home)}</span>
        <span className="text-muted">{label}</span>
        <span className="fw-semibold">{fmtVal(away)}</span>
      </div>
      <div className="progress" style={{ height: 6 }}>
        <div className="progress-bar bg-success" style={{ width: `${homeBar}%` }} />
        <div className="progress-bar bg-danger" style={{ width: `${awayBar}%` }} />
      </div>
    </div>
  )
}
