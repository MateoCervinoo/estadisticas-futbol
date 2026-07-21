export default function FootballLoader() {
  return (
    <div className="football-loader my-4" role="status" aria-live="polite" aria-label="Cargando partidos">
      <div className="d-flex align-items-center justify-content-between gap-3 mb-3">
        <div>
          <div className="skeleton-line skeleton-line-title" />
          <div className="skeleton-line skeleton-line-copy mt-2" />
        </div>
        <div className="skeleton-pill d-none d-sm-block" />
      </div>
      <div className="row g-3">
        {[0, 1, 2].map((item) => (
          <div className="col-12 col-lg-4" key={item}>
            <div className="match-card skeleton-card bg-white border-0 shadow-sm rounded-4">
              <div className="d-flex justify-content-between align-items-center mb-3">
                <div className="skeleton-line skeleton-line-meta" />
                <div className="skeleton-dot" />
              </div>
              <div className="match-teams">
                <div className="team-block">
                  <div className="skeleton-crest" />
                  <div className="skeleton-line skeleton-line-team" />
                </div>
                <div className="score-block skeleton-score" />
                <div className="team-block justify-content-end text-end">
                  <div className="skeleton-line skeleton-line-team" />
                  <div className="skeleton-crest" />
                </div>
              </div>
              <div className="d-flex flex-wrap gap-2 mt-3">
                <div className="skeleton-chip" />
                <div className="skeleton-chip short" />
                <div className="skeleton-chip" />
              </div>
            </div>
          </div>
        ))}
      </div>
      <span className="visually-hidden">Cargando partidos...</span>
    </div>
  )
}
