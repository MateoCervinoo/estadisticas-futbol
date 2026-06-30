import { SelectedTeam, TeamSearchResult, TeamType } from './types'

type TeamSelectorProps = {
  teamType: TeamType
  teamQuery: string
  teams: TeamSearchResult[]
  selectedTeam: SelectedTeam | null
  onChangeTeamType: (type: TeamType) => void
  onChangeQuery: (query: string) => void
  onSelectTeam: (team: SelectedTeam) => void
  onClearTeam: () => void
}

export default function TeamSelector({
  teamType,
  teamQuery,
  teams,
  selectedTeam,
  onChangeTeamType,
  onChangeQuery,
  onSelectTeam,
  onClearTeam,
}: TeamSelectorProps) {
  return (
    <div className="card shadow-sm border-0 rounded-3 mb-4">
      <div className="card-body">
        <div className="btn-group btn-group-sm mb-3" role="group" aria-label="Tipo de equipo">
          <button
            type="button"
            className={`btn ${teamType === 'club' ? 'btn-primary' : 'btn-outline-primary'}`}
            onClick={() => onChangeTeamType('club')}
          >
            Clubes
          </button>
          <button
            type="button"
            className={`btn ${teamType === 'seleccion' ? 'btn-primary' : 'btn-outline-primary'}`}
            onClick={() => onChangeTeamType('seleccion')}
          >
            Selecciones
          </button>
        </div>
        {selectedTeam ? (
          <div className="d-flex align-items-center justify-content-between">
            <span className="fw-semibold">{selectedTeam.nombre}</span>
            <button className="btn btn-sm btn-outline-secondary" onClick={onClearTeam}>Cambiar equipo</button>
          </div>
        ) : (
          <div className="position-relative">
            <label className="form-label small fw-semibold">Buscar equipo</label>
            <input
              className="form-control"
              placeholder="Escribí al menos 2 caracteres..."
              value={teamQuery}
              onChange={(event) => onChangeQuery(event.target.value)}
            />
            {teams.length > 0 && (
              <ul className="list-group position-absolute w-100 shadow" style={{ zIndex: 1050, maxHeight: 250, overflowY: 'auto' }}>
                {teams.map((team) => (
                  <li
                    key={team.id}
                    className="list-group-item list-group-item-action py-2"
                    onClick={() => onSelectTeam(team)}
                    role="button"
                  >
                    {team.codigo_bandera && <span className={`fi fi-${team.codigo_bandera} me-2`} />}
                    {team.nombre}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
