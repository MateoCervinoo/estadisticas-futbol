import { PredictionResponse } from '../../src/services/api'
import { exactScoreMatrix, heatmapClass, probabilityBarClass, topExactScores, topScoreBadgeClass } from './predictionPresentation'

type PredictionModalProps = {
  prediction: PredictionResponse | null
  predLoading: boolean
}

export default function PredictionModal({ prediction, predLoading }: PredictionModalProps) {
  const predictionIsOk = prediction?.status === 'ok' && Array.isArray(prediction.score_matrix)

  return (
    <div>
      <div className="border-bottom border-light pb-3 mb-3">
        <div className="fw-semibold mb-2">Probabilidades</div>
        {predLoading && <div className="text-muted small">Calculando probabilidades...</div>}
        {!predLoading && predictionIsOk && (
          <div className="vstack gap-3">
            {([
              { key: 'home_win' as const, label: 'Local', value: Number(prediction.home_win ?? 0) },
              { key: 'draw' as const, label: 'Empate', value: Number(prediction.draw ?? 0) },
              { key: 'away_win' as const, label: 'Visitante', value: Number(prediction.away_win ?? 0) },
            ]).map((item) => {
              const barClass = probabilityBarClass(item.key)
              return (
                <div key={item.key}>
                  <div className="d-flex justify-content-between small mb-1">
                    <span className="fw-semibold">{item.label}</span>
                    <span>{item.value}%</span>
                  </div>
                  <div className="progress" role="progressbar" aria-valuenow={item.value} aria-valuemin={0} aria-valuemax={100}>
                    <div className={`progress-bar ${barClass}`} style={{ width: `${item.value}%` }} />
                  </div>
                </div>
              )
            })}
          </div>
        )}
        {!predLoading && prediction && !predictionIsOk && (
          <div className="alert alert-warning small mb-0">
            {prediction.message || 'Datos insuficientes para generar una predicción confiable.'}
          </div>
        )}
        {!predLoading && !prediction && (
          <div className="text-muted small">No hay predicción disponible por un error técnico o falta de conexión.</div>
        )}
      </div>

      {!predLoading && predictionIsOk && (
        <div>
          <div className="fw-semibold mb-2">Top 3 resultados posibles</div>
          <div className="d-flex flex-wrap gap-2">
            {topExactScores(prediction).map((score, index) => (
              <span key={`${score.home}-${score.away}`} className={`badge ${topScoreBadgeClass(index)} text-wrap fs-6`}>
                {score.home}-{score.away} - {score.prob}%
              </span>
            ))}
          </div>

          <hr className="text-muted" />

          <h6 className="text-muted fw-semibold mb-2">Matriz de Resultados Posibles (%)</h6>
          {(() => {
            const matrix = exactScoreMatrix(prediction)
            const maxValue = Math.max(...matrix.flat(), 0)

            return (
              <div className="table-responsive">
                <div className="d-flex justify-content-between small text-muted mb-2 px-1">
                  <span>Filas: Local</span>
                  <span>Columnas: Visitante</span>
                </div>
                <table className="table table-bordered table-sm text-center align-middle mb-0">
                  <thead className="table-light">
                    <tr>
                      <th scope="col" className="small text-muted">Marcador</th>
                      {[0, 1, 2, 3, 4].map((goals) => (
                        <th key={`away-${goals}`} scope="col">
                          {goals === 4 ? '4+' : goals}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {matrix.map((row, homeGoals) => (
                      <tr key={`home-${homeGoals}`}>
                        <th scope="row" className="table-light">
                          {homeGoals === 4 ? '4+' : homeGoals}
                        </th>
                        {[0, 1, 2, 3, 4].map((awayGoals) => {
                          const value = row[awayGoals] ?? 0

                          return (
                            <td key={`${homeGoals}-${awayGoals}`} className={heatmapClass(value, maxValue)}>
                              {value}%
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          })()}
        </div>
      )}
    </div>
  )
}
