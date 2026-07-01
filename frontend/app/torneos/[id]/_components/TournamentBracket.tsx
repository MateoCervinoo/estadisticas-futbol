import { BracketRound } from '../../../../src/services/api'
import { flagClass } from '../../../(home)/matchPresentation'

type TournamentBracketProps = {
  bracket: BracketRound[] | null
}

export default function TournamentBracket({ bracket }: TournamentBracketProps) {
  if (!bracket || bracket.length === 0) {
    return <div className="text-muted text-center py-5">No hay eliminatorias para este torneo.</div>
  }

  return (
    <div className="vstack gap-4">
      {bracket.filter((round) => round.stage !== 'GROUP_STAGE').map((round) => (
        <div key={round.stage}>
          <h5 className="mb-3">{round.label}</h5>
          <div className="row">
            {round.matches.map((match) => (
              <div key={match.partido_id} className="col-12 col-md-6 col-lg-4 mb-2">
                <div className="card bg-white shadow-sm border-0 rounded-3 p-3">
                  <div className="d-flex align-items-center justify-content-between gap-2">
                    <div className="d-flex align-items-center flex-fill">
                      {match.home_crest_url ? (
                        <img src={match.home_crest_url} alt={`Escudo ${match.home_team}`} width={18} height={18} className="me-2" />
                      ) : (
                        <span className={`${flagClass(match.home_team, match.home_codigo_bandera)} me-2`} />
                      )}
                      <div className="fw-semibold small">{match.home_team}</div>
                    </div>
                    <div className="text-center">
                      {match.home_score !== null ? (
                        <span className="fw-bold">{match.home_score} - {match.away_score}</span>
                      ) : <span className="text-muted small">vs</span>}
                    </div>
                    <div className="d-flex align-items-center justify-content-end flex-fill">
                      <div className="fw-semibold small text-end me-2">{match.away_team}</div>
                      {match.away_crest_url ? (
                        <img src={match.away_crest_url} alt={`Escudo ${match.away_team}`} width={18} height={18} className="ms-2" />
                      ) : (
                        <span className={`${flagClass(match.away_team, match.away_codigo_bandera)} ms-2`} />
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
