import { BracketRound } from '../../../../src/services/api'
import { flagClass, formatDate } from '../../../(home)/matchPresentation'

type TournamentBracketProps = {
  bracket: BracketRound[] | null
}

export default function TournamentBracket({ bracket }: TournamentBracketProps) {
  const knockoutRounds = bracket?.filter((round) => round.stage !== 'GROUP_STAGE') ?? []

  if (knockoutRounds.length === 0) {
    return <div className="text-muted text-center py-5">No hay eliminatorias para este torneo.</div>
  }

  const missingTeams = knockoutRounds.some((round) => round.matches.some((match) => !match.home_team || !match.away_team))
  const pendingScores = knockoutRounds.some((round) => round.matches.some((match) => match.home_score === null || match.away_score === null))

  return (
    <div className="vstack gap-4">
      {(missingTeams || pendingScores) && (
        <div className="alert alert-light border mb-0 small text-muted">
          {missingTeams ? 'Hay cruces con equipos TBD o sin datos completos de la fuente. ' : ''}
          {pendingScores ? 'Los partidos sin marcador se muestran como pendientes.' : ''}
        </div>
      )}
      {knockoutRounds.map((round) => (
        <section key={round.stage} className="card bg-white border-0 shadow-sm rounded-4 p-3 p-md-4">
          <div className="d-flex align-items-center justify-content-between mb-3">
            <h5 className="mb-0">{round.label}</h5>
            <span className="badge text-bg-secondary">{round.matches.length} partidos</span>
          </div>
          <div className="row">
            {round.matches.map((match) => (
              <div key={match.partido_id} className="col-12 col-md-6 col-lg-4 mb-2">
                <div className="card bg-white shadow-sm border-0 rounded-3 p-3">
                  <div className="small text-muted mb-2">{match.fecha ? formatDate(match.fecha) : 'Fecha a confirmar'}</div>
                  <div className="d-flex align-items-center justify-content-between gap-2">
                    <div className="d-flex align-items-center flex-fill">
                      {match.home_crest_url ? (
                        <img src={match.home_crest_url} alt={`Escudo ${match.home_team}`} width={18} height={18} className="me-2" />
                      ) : (
                        <span className={`${flagClass(match.home_team, match.home_codigo_bandera)} me-2`} />
                      )}
                      <div className="fw-semibold small">{match.home_team || 'TBD'}</div>
                    </div>
                    <div className="text-center">
                      {match.home_score !== null && match.away_score !== null ? (
                        <span className="fw-bold">{match.home_score} - {match.away_score}</span>
                      ) : <span className="text-muted small">vs</span>}
                    </div>
                    <div className="d-flex align-items-center justify-content-end flex-fill">
                      <div className="fw-semibold small text-end me-2">{match.away_team || 'TBD'}</div>
                      {match.away_crest_url ? (
                        <img src={match.away_crest_url} alt={`Escudo ${match.away_team}`} width={18} height={18} className="ms-2" />
                      ) : (
                        <span className={`${flagClass(match.away_team, match.away_codigo_bandera)} ms-2`} />
                      )}
                    </div>
                  </div>
                  <div className="small text-muted mt-2">Estado: {match.estado || 'sin estado'}</div>
                </div>
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
