import { rawGroupLabel, rawStageLabel, TOURNAMENT_LABELS } from './matchPresentation'

type MatchFiltersProps = {
  loading: boolean
  hasPartidos: boolean
  filteredCount: number
  showFilters: boolean
  setShowFilters: (value: boolean | ((current: boolean) => boolean)) => void
  selectedYear: number | undefined
  setSelectedYear: (year: number | undefined) => void
  aniosDisponibles: number[]
  showFavoritesOnly: boolean
  setShowFavoritesOnly: (value: boolean | ((current: boolean) => boolean)) => void
  favoritesCount: number
  hasActiveServerFilters: boolean
  competitionOptions: string[]
  competitionFilter: string
  setCompetitionFilter: (competition: string) => void
  showStageFilter: boolean
  stageOptions: string[]
  stageFilter: string
  setStageFilter: (stage: string) => void
  showGroupFilter: boolean
  groupOptions: string[]
  groupFilter: string
  setGroupFilter: (group: string) => void
  showMatchdayFilter: boolean
  matchdayOptions: number[]
  matchdayFilter: number | undefined
  setMatchdayFilter: (matchday: number | undefined) => void
}

export default function MatchFilters({
  loading,
  hasPartidos,
  filteredCount,
  showFilters,
  setShowFilters,
  selectedYear,
  setSelectedYear,
  aniosDisponibles,
  showFavoritesOnly,
  setShowFavoritesOnly,
  favoritesCount,
  hasActiveServerFilters,
  competitionOptions,
  competitionFilter,
  setCompetitionFilter,
  showStageFilter,
  stageOptions,
  stageFilter,
  setStageFilter,
  showGroupFilter,
  groupOptions,
  groupFilter,
  setGroupFilter,
  showMatchdayFilter,
  matchdayOptions,
  matchdayFilter,
  setMatchdayFilter,
}: MatchFiltersProps) {
  return (
    <div className="border-top mt-3 pt-3">
      <div className="d-flex align-items-center justify-content-between gap-2">
        <div>
          <div className="fw-semibold">Filtros</div>
          <div className="small text-muted">Filtrá por año, competencia y opciones propias del torneo</div>
        </div>
        <div className="d-flex align-items-center gap-2">
          {!loading && hasPartidos && (
            <span className="badge bg-secondary rounded-pill">{filteredCount} partidos</span>
          )}
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-2"
            onClick={() => setShowFilters((value) => !value)}
          >
            <span>{showFilters ? 'Ocultar' : 'Mostrar'}</span>
            <span aria-hidden="true">{showFilters ? '▴' : '▾'}</span>
          </button>
        </div>
      </div>

      {showFilters && (
        <div className="pt-3">
          <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
            <span className="small text-muted">Año:</span>
            <button
              className={`btn btn-outline-secondary btn-sm rounded-pill ${selectedYear === undefined ? 'active' : ''}`}
              onClick={() => setSelectedYear(undefined)}
            >
              Todos
            </button>
            {aniosDisponibles.map((year) => (
              <button
                key={year}
                className={`btn btn-outline-secondary btn-sm rounded-pill ${selectedYear === year ? 'active' : ''}`}
                onClick={() => setSelectedYear(year)}
              >
                {year}
              </button>
            ))}
          </div>

          <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
            <button
              className={`btn btn-sm rounded-pill ${showFavoritesOnly ? 'btn-warning' : 'btn-outline-warning'}`}
              onClick={() => setShowFavoritesOnly((value) => !value)}
              title="Filtra sobre los partidos ya cargados por los filtros activos"
            >
              ⭐ Mis Partidos {favoritesCount > 0 && `(${favoritesCount})`}
            </button>
            {showFavoritesOnly && !hasActiveServerFilters && (
              <span className="small text-muted">Aplicá un filtro de servidor para cargar partidos favoritos.</span>
            )}
          </div>

          <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
            <span className="small text-muted">Competición:</span>
            {competitionOptions.map((opt) => (
              <button
                key={opt}
                className={`btn btn-outline-secondary btn-sm rounded-pill ${competitionFilter === opt ? 'active' : ''}`}
                onClick={() => setCompetitionFilter(opt)}
              >
                {TOURNAMENT_LABELS[opt] ?? opt}
              </button>
            ))}
          </div>

          {showStageFilter && (
            <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
              <span className="small text-muted">Etapa:</span>
              {stageOptions.map((opt) => (
                <button
                  key={`stage-${opt}`}
                  className={`btn btn-outline-secondary btn-sm rounded-pill ${stageFilter === opt ? 'active' : ''}`}
                  onClick={() => setStageFilter(opt)}
                >
                  {opt === 'Todos' ? opt : rawStageLabel(opt)}
                </button>
              ))}
            </div>
          )}

          {showGroupFilter && (
            <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
              <span className="small text-muted">Grupo:</span>
              {groupOptions.map((opt) => (
                <button
                  key={`group-${opt}`}
                  className={`btn btn-outline-secondary btn-sm rounded-pill ${groupFilter === opt ? 'active' : ''}`}
                  onClick={() => setGroupFilter(opt)}
                >
                  {opt === 'Todos' ? opt : rawGroupLabel(opt)}
                </button>
              ))}
            </div>
          )}

          {showMatchdayFilter && (
            <div className="d-flex flex-wrap align-items-center gap-2">
              <span className="small text-muted">Jornada:</span>
              <button
                className={`btn btn-outline-secondary btn-sm rounded-pill ${matchdayFilter === undefined ? 'active' : ''}`}
                onClick={() => setMatchdayFilter(undefined)}
              >
                Todas
              </button>
              {matchdayOptions.map((matchday) => (
                <button
                  key={`matchday-${matchday}`}
                  className={`btn btn-outline-secondary btn-sm rounded-pill ${matchdayFilter === matchday ? 'active' : ''}`}
                  onClick={() => setMatchdayFilter(matchday)}
                >
                  Jornada {matchday}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
