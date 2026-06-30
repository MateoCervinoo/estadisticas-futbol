import StatRow from '../../../../components/StatRow'
import { Partido, PartidoEstadisticas } from '../../../../src/services/api'

type TournamentMatchDetailModalProps = {
  selectedMatch: Partido
  currentStats: PartidoEstadisticas | null
  statsLoading: boolean
  onClose: () => void
}

export default function TournamentMatchDetailModal({ selectedMatch, currentStats, statsLoading, onClose }: TournamentMatchDetailModalProps) {
  return (
    <>
      <div className="modal fade show d-block" tabIndex={-1} onClick={onClose}>
        <div className="modal-dialog modal-lg modal-dialog-centered" onClick={(event) => event.stopPropagation()}>
          <div className="modal-content bg-white text-dark border-0 shadow">
            <div className="modal-header bg-light">
              <h5 className="modal-title">{selectedMatch.home_team} vs {selectedMatch.away_team}</h5>
              <button className="btn-close" onClick={onClose} />
            </div>
            <div className="modal-body">
              <div className="d-flex align-items-center justify-content-between py-3">
                <div className="fw-semibold">{selectedMatch.home_team}</div>
                <div className="fw-bold fs-4">{selectedMatch.home_score} - {selectedMatch.away_score}</div>
                <div className="fw-semibold">{selectedMatch.away_team}</div>
              </div>
              {statsLoading && <div className="text-muted small text-center">Cargando estadísticas...</div>}
              {!statsLoading && currentStats && (
                <div className="vstack gap-2">
                  {currentStats.xg_local != null && <StatRow label="xG" home={currentStats.xg_local} away={currentStats.xg_visitante} fmt="float" />}
                  {currentStats.remates_local != null && <StatRow label="Remates" home={currentStats.remates_local} away={currentStats.remates_visitante} />}
                  {currentStats.posesion_local != null && <StatRow label="Posesión" home={currentStats.posesion_local} away={currentStats.posesion_visitante} fmt="pct" />}
                </div>
              )}
              {!statsLoading && !currentStats && <div className="text-muted small text-center py-3">Estadísticas no disponibles.</div>}
            </div>
            <div className="modal-footer bg-light">
              <button className="btn btn-secondary" onClick={onClose}>Cerrar</button>
            </div>
          </div>
        </div>
      </div>
      <div className="modal-backdrop fade show" />
    </>
  )
}
