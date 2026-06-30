import { EquipoPerfil } from '../../../../src/services/api'
import { formatShortDate } from './teamPresentation'

type UpcomingMatchesProps = {
  proximos: EquipoPerfil['proximos']
}

export default function UpcomingMatches({ proximos }: UpcomingMatchesProps) {
  if (proximos.length === 0) return null

  return (
    <div className="card bg-white shadow-sm border-0 rounded-3 p-4 mb-4">
      <h6 className="fw-semibold mb-3">Próximos partidos</h6>
      <div className="vstack gap-2">
        {proximos.map((match) => (
          <div key={match.partido_id} className="d-flex justify-content-between align-items-center small">
            <span>{match.local ? 'Local' : 'Visitante'} vs <strong>{match.rival}</strong></span>
            <span className="text-muted">{formatShortDate(match.fecha)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
