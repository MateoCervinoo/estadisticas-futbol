import { BracketRound } from '../../../../src/services/api'

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
                    <div className="fw-semibold small flex-fill">{match.home_team}</div>
                    <div className="text-center">
                      {match.home_score !== null ? (
                        <span className="fw-bold">{match.home_score} - {match.away_score}</span>
                      ) : <span className="text-muted small">vs</span>}
                    </div>
                    <div className="fw-semibold small flex-fill text-end">{match.away_team}</div>
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
