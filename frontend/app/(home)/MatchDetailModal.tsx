import { Partido, PartidoEstadisticas } from '../../src/services/api'
import StatRow from '../../components/StatRow'
import { flagClass, formatScore } from './matchPresentation'

type MatchDetailModalProps = {
  selectedMatch: Partido
  currentStats: PartidoEstadisticas | null
  statsLoading: boolean
}

export default function MatchDetailModal({ selectedMatch, currentStats, statsLoading }: MatchDetailModalProps) {
  return (
    <div>
      <div className="border-bottom border-light pb-3 mb-3">
        <div className="d-flex align-items-center justify-content-between gap-3">
          <div className="d-flex align-items-center gap-2">
            <span className={`${flagClass(selectedMatch.home_team, selectedMatch.home_codigo_bandera)}`} />
            <div>
              <div className="fw-semibold">{selectedMatch.home_team}</div>
              <div className="small text-muted">Local</div>
            </div>
          </div>

          <div className="text-center">
            <div className="fw-bold fs-4">{formatScore(selectedMatch.home_score)} - {formatScore(selectedMatch.away_score)}</div>
            {(selectedMatch.ht_home_score != null || selectedMatch.ht_away_score != null) && (
              <div className="small text-muted">HT: {formatScore(selectedMatch.ht_home_score)} - {formatScore(selectedMatch.ht_away_score)}</div>
            )}
          </div>

          <div className="d-flex align-items-center gap-2 text-end">
            <div>
              <div className="fw-semibold">{selectedMatch.away_team}</div>
              <div className="small text-muted">Visitante</div>
            </div>
            <span className={`${flagClass(selectedMatch.away_team, selectedMatch.away_codigo_bandera)}`} />
          </div>
        </div>
      </div>

      {statsLoading && <div className="text-muted small text-center py-3">Cargando estadísticas...</div>}

      {!statsLoading && currentStats && (
        <div>
          <div className="fw-semibold mb-2">Estadísticas</div>
          <div className="vstack gap-2">
            {currentStats.xg_local != null && currentStats.xg_visitante != null && (
              <StatRow label="xG" home={currentStats.xg_local} away={currentStats.xg_visitante} fmt="float" />
            )}
            {currentStats.remates_local != null && (
              <StatRow label="Remates" home={currentStats.remates_local} away={currentStats.remates_visitante} />
            )}
            {currentStats.remates_puerta_local != null && (
              <StatRow label="Remates a puerta" home={currentStats.remates_puerta_local} away={currentStats.remates_puerta_visitante} />
            )}
            {currentStats.posesion_local != null && (
              <StatRow label="Posesión" home={currentStats.posesion_local} away={currentStats.posesion_visitante} fmt="pct" />
            )}
            {currentStats.corners_local != null && (
              <StatRow label="Córners" home={currentStats.corners_local} away={currentStats.corners_visitante} />
            )}
            {currentStats.faltas_local != null && (
              <StatRow label="Faltas" home={currentStats.faltas_local} away={currentStats.faltas_visitante} />
            )}
            {currentStats.tarjetas_amarillas_local != null && (
              <StatRow label="Amarillas" home={currentStats.tarjetas_amarillas_local} away={currentStats.tarjetas_amarillas_visitante} />
            )}
            {currentStats.tarjetas_rojas_local != null && (
              <StatRow label="Rojas" home={currentStats.tarjetas_rojas_local} away={currentStats.tarjetas_rojas_visitante} />
            )}
            {currentStats.fueras_juego_local != null && (
              <StatRow label="Fueras de juego" home={currentStats.fueras_juego_local} away={currentStats.fueras_juego_visitante} />
            )}
            {currentStats.paradas_local != null && (
              <StatRow label="Paradas" home={currentStats.paradas_local} away={currentStats.paradas_visitante} />
            )}
          </div>
        </div>
      )}

      {!statsLoading && !currentStats && (
        <div className="small text-muted text-center py-3">
          Estadísticas avanzadas no disponibles para este partido.
        </div>
      )}
    </div>
  )
}
