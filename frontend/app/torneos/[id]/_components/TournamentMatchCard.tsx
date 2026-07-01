import { Partido } from '../../../../src/services/api'
import { flagClass, formatDate, formatScore, isPlayed, rawGroupLabel, rawStageLabel } from '../../../(home)/matchPresentation'

type TournamentMatchCardProps = {
  partido: Partido
  onOpenDetail: (partido: Partido) => void
}

export default function TournamentMatchCard({ partido, onOpenDetail }: TournamentMatchCardProps) {
  const played = isPlayed(partido)

  return (
    <div className="col-12 col-md-6 mb-3">
      <div className="card bg-white shadow-sm border-0 rounded-3 p-4">
        <div className="d-flex justify-content-between align-items-start gap-3">
          <div className="small text-muted">
            {rawStageLabel(partido.stage?.trim() || '') || partido.stage || ''}
            {partido.group ? ` · ${rawGroupLabel(partido.group)}` : ''}
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
            ) : <div className="text-muted">vs</div>}
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
            <button className="btn btn-outline-secondary rounded-pill btn-sm" onClick={() => onOpenDetail(partido)}>Ver detalle</button>
          ) : (
            <span className="text-muted small">Próximamente</span>
          )}
        </div>
      </div>
    </div>
  )
}
