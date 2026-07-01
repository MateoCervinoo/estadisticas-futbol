import { Partido } from '../../src/services/api'
import { flagClass, formatDate, formatScore, groupOf, isPlayed, stageOf, tournamentOf } from './matchPresentation'

type MatchCardProps = {
  partido: Partido
  isFavorite: boolean
  onToggleFavorite: (partidoId: number) => void
  onOpenDetail: (partido: Partido) => void
  onOpenSimulate: (partido: Partido) => void
}

export default function MatchCard({ partido, isFavorite, onToggleFavorite, onOpenDetail, onOpenSimulate }: MatchCardProps) {
  const played = isPlayed(partido)
  const hasCrests = Boolean(partido.home_crest_url && partido.away_crest_url)
  const confidenceLabel = played ? 'Datos cerrados' : partido.fixture_id ? 'Modelo listo' : 'Confianza limitada'

  return (
    <div className="col-12 col-xl-6">
      <div className={`match-card h-100 ${isFavorite ? 'is-favorite' : ''}`}>
        <div className="d-flex justify-content-between align-items-start gap-3">
          <div className="match-meta d-flex align-items-center gap-2">
            <button
              type="button"
              className={`favorite-button ${isFavorite ? 'active' : ''}`}
              onClick={() => onToggleFavorite(partido.id)}
              aria-pressed={isFavorite}
              aria-label={isFavorite ? 'Quitar de favoritos' : 'Agregar a favoritos'}
            >
              {isFavorite ? '★' : '☆'}
            </button>
            <span className="text-truncate">{tournamentOf(partido)}{stageOf(partido) ? ` · ${stageOf(partido)}` : ''}{partido.group ? ` · ${groupOf(partido)}` : ''}</span>
            {partido.status === 'IN_PLAY' && (
              <span className="badge bg-danger rounded-pill live-pulse small">EN VIVO</span>
            )}
          </div>
          <div className="small text-muted text-end">{formatDate(partido.date)}</div>
        </div>

        <div className="match-teams mt-3">
          <div className="team-block">
            {partido.home_crest_url ? (
              <img src={partido.home_crest_url} alt={`Escudo ${partido.home_team}`} width={30} height={30} className="team-crest" />
            ) : (
              <span className={`${flagClass(partido.home_team, partido.home_codigo_bandera)} team-flag`} />
            )}
            <div className="team-name">{partido.home_team}</div>
          </div>

          <div className="score-block">
            {played ? (
              <div className="score-value">{formatScore(partido.home_score)} - {formatScore(partido.away_score)}</div>
            ) : (
              <div className="vs-value">vs</div>
            )}
          </div>

          <div className="team-block text-end justify-content-end">
            <div className="team-name">{partido.away_team}</div>
            {partido.away_crest_url ? (
              <img src={partido.away_crest_url} alt={`Escudo ${partido.away_team}`} width={30} height={30} className="team-crest" />
            ) : (
              <span className={`${flagClass(partido.away_team, partido.away_codigo_bandera)} team-flag`} />
            )}
          </div>
        </div>

        <div className="match-insights mt-3">
          <span>{confidenceLabel}</span>
          <span>{hasCrests ? 'Escudos OK' : 'Fallback visual'}</span>
          {partido.matchday && <span>Jornada {partido.matchday}</span>}
        </div>

        <div className="mt-3 d-flex flex-wrap justify-content-between align-items-center gap-2">
          <div className="d-flex gap-2">
            <button className="btn btn-sm btn-outline-secondary rounded-pill" disabled title="Próximamente">
              Compartir
            </button>
            <button className="btn btn-sm btn-outline-secondary rounded-pill" disabled title="Próximamente">
              Exportar
            </button>
          </div>
          {played ? (
            <button className="btn btn-outline-secondary rounded-pill" onClick={() => onOpenDetail(partido)}>Ver detalle</button>
          ) : (
            <button className="btn btn-success rounded-pill" onClick={() => onOpenSimulate(partido)}>Simular</button>
          )}
        </div>
      </div>
    </div>
  )
}
