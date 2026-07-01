import { Partido, TablaRow } from '../../../../src/services/api'
import { flagClass, isPlayed } from '../../../(home)/matchPresentation'

type TournamentStatsProps = {
  tabla: TablaRow[] | null
  partidos: Partido[] | null
}

const top = (rows: TablaRow[], sorter: (a: TablaRow, b: TablaRow) => number) => [...rows].sort(sorter).slice(0, 5)

function LeaderCard({ title, rows, value }: { title: string; rows: TablaRow[]; value: (row: TablaRow) => string }) {
  return (
    <div className="card bg-white shadow-sm border-0 rounded-4 p-4 h-100">
      <h6 className="fw-semibold mb-3">{title}</h6>
      <div className="vstack gap-2 small">
        {rows.map((row) => (
          <div key={row.equipo_id} className="d-flex align-items-center justify-content-between gap-3">
            <span className="d-flex align-items-center gap-2"><span className={flagClass(row.equipo, row.codigo_bandera)} />{row.equipo}</span>
            <span className="fw-semibold text-nowrap">{value(row)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function TournamentStats({ tabla, partidos }: TournamentStatsProps) {
  if (!tabla || tabla.length === 0) return <div className="text-muted text-center py-5">No hay estadísticas para este torneo.</div>

  const totalPJ = tabla.reduce((sum, row) => sum + row.pj, 0)
  const totalGF = tabla.reduce((sum, row) => sum + row.gf, 0)
  const avg = totalPJ > 0 ? (totalGF / totalPJ) : 0
  const hasXg = tabla.some((row) => row.xg_favor > 0 || row.xg_contra > 0 || row.xg_diff !== 0)
  const playedMatches = partidos?.filter(isPlayed).length ?? 0
  const formRows = top(tabla.filter((row) => row.pj > 0), (a, b) => (b.pg / b.pj) - (a.pg / a.pj) || b.pts - a.pts || b.gd - a.gd)

  return (
    <div className="row g-4">
      <div className="col-12">
        <div className="card bg-dark text-white border-0 rounded-4 p-4">
          <div className="row g-3 text-center text-md-start">
            <div className="col-6 col-md-3"><div className="fs-3 fw-bold">{playedMatches}</div><div className="small text-white-50">Partidos jugados</div></div>
            <div className="col-6 col-md-3"><div className="fs-3 fw-bold">{totalGF}</div><div className="small text-white-50">Goles</div></div>
            <div className="col-6 col-md-3"><div className="fs-3 fw-bold">{avg.toFixed(2)}</div><div className="small text-white-50">Goles/partido</div></div>
            <div className="col-6 col-md-3"><div className="fs-3 fw-bold">{hasXg ? 'Si' : 'No'}</div><div className="small text-white-50">Cobertura xG</div></div>
          </div>
        </div>
      </div>
      <div className="col-12 col-md-6">
        <LeaderCard title="Ataque" rows={top(tabla, (a, b) => b.gf - a.gf)} value={(row) => `${row.gf} goles`} />
      </div>
      <div className="col-12 col-md-6">
        <LeaderCard title="Defensa" rows={top(tabla, (a, b) => a.gc - b.gc || b.pts - a.pts)} value={(row) => `${row.gc} recibidos`} />
      </div>
      {hasXg && <div className="col-12 col-md-6"><LeaderCard title="xG Favor" rows={top(tabla, (a, b) => b.xg_favor - a.xg_favor)} value={(row) => row.xg_favor.toFixed(2)} /></div>}
      {hasXg && <div className="col-12 col-md-6"><LeaderCard title="xGA Bajo" rows={top(tabla, (a, b) => a.xg_contra - b.xg_contra)} value={(row) => row.xg_contra.toFixed(2)} /></div>}
      <div className="col-12 col-md-6">
        <LeaderCard title="Mejor Forma" rows={formRows} value={(row) => `${row.pg}-${row.pe}-${row.pp}`} />
      </div>
      {!hasXg && <div className="col-12"><div className="alert alert-light border small text-muted mb-0">No hay cobertura xG/xGA para esta temporada o la fuente no la informó.</div></div>}
    </div>
  )
}
