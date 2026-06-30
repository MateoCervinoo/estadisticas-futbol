import { Comparacion } from '../../../../src/services/api'
import ComparisonRadar from './ComparisonRadar'
import { formatShortDate } from './teamPresentation'

type TeamComparisonProps = {
  compareId: string
  comparacion: Comparacion | null
  compLoading: boolean
  radarData: { label: string; v1: number; v2: number }[]
  maxRadar: number
  onCompareIdChange: (value: string) => void
  onCompare: () => void
}

export default function TeamComparison({
  compareId,
  comparacion,
  compLoading,
  radarData,
  maxRadar,
  onCompareIdChange,
  onCompare,
}: TeamComparisonProps) {
  return (
    <div className="card bg-white shadow-sm border-0 rounded-3 p-4">
      <h6 className="fw-semibold mb-3">Comparar con otro equipo</h6>
      <div className="d-flex gap-2 mb-3">
        <input
          className="form-control form-control-sm"
          placeholder="ID del equipo"
          value={compareId}
          onChange={(event) => onCompareIdChange(event.target.value)}
        />
        <button className="btn btn-primary btn-sm" onClick={onCompare} disabled={compLoading}>
          {compLoading ? '...' : 'Comparar'}
        </button>
      </div>

      {comparacion && (
        <div>
          <div className="table-responsive">
            <table className="table table-sm table-bordered align-middle">
              <thead className="table-light">
                <tr>
                  <th>Métrica</th>
                  <th className="text-center">{comparacion.equipo1.nombre}</th>
                  <th className="text-center">{comparacion.equipo2.nombre}</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { label: 'Partidos', v1: comparacion.equipo1.stats.pj, v2: comparacion.equipo2.stats.pj },
                  { label: 'Victorias', v1: comparacion.equipo1.stats.pg, v2: comparacion.equipo2.stats.pg },
                  { label: 'Empates', v1: comparacion.equipo1.stats.pe, v2: comparacion.equipo2.stats.pe },
                  { label: 'Derrotas', v1: comparacion.equipo1.stats.pp, v2: comparacion.equipo2.stats.pp },
                  { label: 'Goles Favor', v1: comparacion.equipo1.stats.gf, v2: comparacion.equipo2.stats.gf },
                  { label: 'Goles Contra', v1: comparacion.equipo1.stats.gc, v2: comparacion.equipo2.stats.gc },
                  { label: 'Diferencia', v1: comparacion.equipo1.stats.gd, v2: comparacion.equipo2.stats.gd },
                  { label: 'xG Favor', v1: comparacion.equipo1.stats.xg_favor, v2: comparacion.equipo2.stats.xg_favor },
                  { label: 'xG Contra', v1: comparacion.equipo1.stats.xg_contra, v2: comparacion.equipo2.stats.xg_contra },
                  { label: 'Puntos', v1: comparacion.equipo1.stats.pts, v2: comparacion.equipo2.stats.pts },
                ].map((row) => {
                  const better = row.v1 > row.v2 ? 'text-success fw-bold' : row.v1 < row.v2 ? 'text-danger' : ''
                  return (
                    <tr key={row.label}>
                      <td>{row.label}</td>
                      <td className={`text-center ${better}`}>{row.v1}</td>
                      <td className={`text-center ${row.v1 < row.v2 ? 'text-success fw-bold' : row.v1 > row.v2 ? 'text-danger' : ''}`}>{row.v2}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          <ComparisonRadar comparacion={comparacion} radarData={radarData} maxRadar={maxRadar} />

          {comparacion.h2h.matches.length > 0 && (
            <div className="mt-4">
              <h6 className="fw-semibold mb-2">Historial H2H</h6>
              <div className="d-flex gap-3 mb-3">
                <span className="badge bg-success">{comparacion.equipo1.nombre}: {comparacion.h2h.eq1_wins}V</span>
                <span className="badge bg-warning text-dark">Empates: {comparacion.h2h.draws}</span>
                <span className="badge bg-danger">{comparacion.equipo2.nombre}: {comparacion.h2h.eq2_wins}V</span>
              </div>
              <div className="vstack gap-1 small">
                {comparacion.h2h.matches.map((match, index) => (
                  <div key={index} className="d-flex justify-content-between">
                    <span className="fw-semibold">{match.eq1_goals} - {match.eq2_goals}</span>
                    <span className="text-muted">{formatShortDate(match.fecha)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
