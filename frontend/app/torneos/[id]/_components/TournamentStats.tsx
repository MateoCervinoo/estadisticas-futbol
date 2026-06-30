import { TablaRow } from '../../../../src/services/api'

type TournamentStatsProps = {
  tabla: TablaRow[] | null
}

export default function TournamentStats({ tabla }: TournamentStatsProps) {
  if (!tabla || tabla.length === 0) return null

  const totalPJ = tabla.reduce((sum, row) => sum + row.pj, 0)
  const totalGF = tabla.reduce((sum, row) => sum + row.gf, 0)
  const avg = totalPJ > 0 ? (totalGF / totalPJ) : 0

  return (
    <div className="row g-4">
      <div className="col-12 col-md-6">
        <div className="card bg-white shadow-sm border-0 rounded-3 p-4">
          <h6 className="fw-semibold mb-3">Ataque</h6>
          <div className="vstack gap-2 small">
            {[...tabla].sort((a, b) => b.gf - a.gf).slice(0, 5).map((row) => (
              <div key={row.equipo_id} className="d-flex justify-content-between">
                <span>{row.equipo}</span><span className="fw-semibold">{row.gf} goles</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="col-12 col-md-6">
        <div className="card bg-white shadow-sm border-0 rounded-3 p-4">
          <h6 className="fw-semibold mb-3">Defensa</h6>
          <div className="vstack gap-2 small">
            {[...tabla].sort((a, b) => a.gc - b.gc).slice(0, 5).map((row) => (
              <div key={row.equipo_id} className="d-flex justify-content-between">
                <span>{row.equipo}</span><span className="fw-semibold">{row.gc} recibidos</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="col-12 col-md-6">
        <div className="card bg-white shadow-sm border-0 rounded-3 p-4">
          <h6 className="fw-semibold mb-3">xG Favor</h6>
          <div className="vstack gap-2 small">
            {[...tabla].sort((a, b) => b.xg_favor - a.xg_favor).slice(0, 5).map((row) => (
              <div key={row.equipo_id} className="d-flex justify-content-between">
                <span>{row.equipo}</span><span className="fw-semibold">{row.xg_favor}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="col-12 col-md-6">
        <div className="card bg-white shadow-sm border-0 rounded-3 p-4">
          <h6 className="fw-semibold mb-3">Promedio de Goles</h6>
          <div className="text-center"><span className="fs-3 fw-bold">{avg.toFixed(2)}</span><div className="small text-muted">goles/partido</div></div>
        </div>
      </div>
    </div>
  )
}
