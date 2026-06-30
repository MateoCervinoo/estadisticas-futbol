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

  return (
    <div className="col-12 col-md-6 mb-3">
      <div className="card bg-white text-dark shadow-sm border-0 rounded-3 mb-3 p-4 h-100">
        <div className="d-flex justify-content-between align-items-start gap-3">
          <div className="small text-muted d-flex align-items-center gap-2">
            <span
              role="button"
              className={`${isFavorite ? 'text-warning' : 'text-muted'}`}
              onClick={() => onToggleFavorite(partido.id)}
              style={{ cursor: 'pointer', fontSize: '1rem' }}
              title={isFavorite ? 'Quitar de favoritos' : 'Agregar a favoritos'}
            >
              {isFavorite ? '★' : '☆'}
            </span>
            {tournamentOf(partido)}{stageOf(partido) ? ` · ${stageOf(partido)}` : ''}{partido.group ? ` · ${groupOf(partido)}` : ''}
            {partido.status === 'IN_PLAY' && (
              <span className="badge bg-danger rounded-pill live-pulse small">EN VIVO</span>
            )}
          </div>
          <div className="small text-muted text-end">{formatDate(partido.date)}</div>
        </div>

        <div className="d-flex align-items-center justify-content-between gap-3 mt-3">
          <div className="d-flex align-items-center flex-fill">
            {partido.home_crest_url ? (
              <img src={partido.home_crest_url} alt={`Escudo ${partido.home_team}`} width={22} height={22} className="me-2" />
            ) : (
              <span className={`${flagClass(partido.home_team, partido.home_codigo_bandera)} me-2`} />
            )}
            <div className="fw-semibold">{partido.home_team}</div>
          </div>

          <div className="text-center">
            {played ? (
              <div className="fs-4 fw-bold">{formatScore(partido.home_score)} - {formatScore(partido.away_score)}</div>
            ) : (
              <div className="text-muted">vs</div>
            )}
          </div>

          <div className="d-flex align-items-center justify-content-end flex-fill">
            <div className="fw-semibold text-end me-2">{partido.away_team}</div>
            {partido.away_crest_url ? (
              <img src={partido.away_crest_url} alt={`Escudo ${partido.away_team}`} width={22} height={22} className="ms-2" />
            ) : (
              <span className={`${flagClass(partido.away_team, partido.away_codigo_bandera)} ms-2`} />
            )}
          </div>
        </div>

        <div className="mt-3 d-flex justify-content-end">
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
