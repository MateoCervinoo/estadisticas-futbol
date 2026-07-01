import { SelectedTeam, TeamSearchResult, TeamType } from './types'

type TeamSelectorProps = {
  teamType: TeamType
  teamQuery: string
  teams: TeamSearchResult[]
  selectedTeam: SelectedTeam | null
  error?: string | null
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
  error,
  onChangeTeamType,
  onChangeQuery,
  onSelectTeam,
  onClearTeam,
}: TeamSelectorProps) {
  return (
    <div className="analysis-selector-card">
      <div className="d-flex align-items-center justify-content-between gap-3 mb-3">
        <div>
          <div className="small text-uppercase fw-semibold text-white-50">Scope</div>
          <div className="fw-semibold text-white">Radar de equipo</div>
        </div>
        <div className="btn-group btn-group-sm analysis-toggle" role="group" aria-label="Tipo de equipo">
          <button
            type="button"
            className={`btn ${teamType === 'club' ? 'active' : ''}`}
            onClick={() => onChangeTeamType('club')}
          >
            Clubes
          </button>
          <button
            type="button"
            className={`btn ${teamType === 'seleccion' ? 'active' : ''}`}
            onClick={() => onChangeTeamType('seleccion')}
          >
            Selecciones
          </button>
        </div>
      </div>
        {selectedTeam ? (
          <div className="analysis-selected-team">
            <div>
              <span className="small text-white-50 d-block">Equipo activo</span>
              <span className="fw-bold text-white">{selectedTeam.nombre}</span>
            </div>
            <button className="btn btn-sm btn-light" onClick={onClearTeam}>Cambiar</button>
          </div>
        ) : (
          <div className="position-relative">
            <label className="form-label small fw-semibold text-white-50">Buscar equipo</label>
            <input
              className="form-control analysis-search-input"
              placeholder="Escribí al menos 2 caracteres..."
              value={teamQuery}
              onChange={(event) => onChangeQuery(event.target.value)}
            />
            {error && <div className="small text-warning mt-2">{error}</div>}
            {teams.length > 0 && (
              <ul className="list-group position-absolute w-100 shadow-lg analysis-search-results">
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
  )
}
