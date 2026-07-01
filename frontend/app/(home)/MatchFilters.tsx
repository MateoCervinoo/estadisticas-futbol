import { rawGroupLabel, rawStageLabel, TOURNAMENT_LABELS } from './matchPresentation'

type MatchFiltersProps = {
  loading: boolean
  hasPartidos: boolean
  filteredCount: number
  showFilters: boolean
  setShowFilters: (value: boolean | ((current: boolean) => boolean)) => void
  selectedYear: number | undefined
  setSelectedYear: (year: number | undefined) => void
  selectedSeason: string
  setSelectedSeason: (season: string) => void
  aniosDisponibles: number[]
  temporadasDisponibles: string[]
  showFavoritesOnly: boolean
  setShowFavoritesOnly: (value: boolean | ((current: boolean) => boolean)) => void
  favoritesCount: number
  hasActiveServerFilters: boolean
  competitionOptions: string[]
  competitionFilter: string
  setCompetitionFilter: (competition: string) => void
  isLeagueFilter: boolean
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
  selectedSeason,
  setSelectedSeason,
  aniosDisponibles,
  temporadasDisponibles,
  showFavoritesOnly,
  setShowFavoritesOnly,
  favoritesCount,
  hasActiveServerFilters,
  competitionOptions,
  competitionFilter,
  setCompetitionFilter,
  isLeagueFilter,
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
  const hasCompetition = competitionFilter !== 'Todos'
  const periodOptions = isLeagueFilter ? temporadasDisponibles : aniosDisponibles
  const periodLabel = isLeagueFilter ? 'Temporada:' : 'Año:'

  const selectYear = (year: number | undefined) => {
    setSelectedSeason('Todos')
    setSelectedYear(year)
  }

  const selectSeason = (season: string) => {
    setSelectedYear(undefined)
    setSelectedSeason(season)
  }

  return (
    <div className="filters-panel mt-3 pt-3">
      <div className="d-flex align-items-center justify-content-between gap-2">
        <div>
          <div className="fw-semibold">Filtros de agenda</div>
          <div className="small text-muted">Primero elegí torneo; después temporada/edición y filtros propios</div>
        </div>
        <div className="d-flex align-items-center gap-2">
          {!loading && hasPartidos && (
            <span className="badge app-count-badge rounded-pill">{filteredCount} partidos</span>
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
          <div className="filter-group mb-3">
            <span className="filter-label">Competición</span>
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

          <div className="filter-group mb-3">
            <span className="filter-label">{periodLabel.replace(':', '')}</span>
            <button
              className={`btn btn-outline-secondary btn-sm rounded-pill ${(isLeagueFilter ? selectedSeason === 'Todos' : selectedYear === undefined) ? 'active' : ''}`}
              onClick={() => isLeagueFilter ? selectSeason('Todos') : selectYear(undefined)}
              disabled={!hasCompetition}
            >
              {isLeagueFilter ? 'Todas' : 'Todos'}
            </button>
            {hasCompetition ? (
              isLeagueFilter ? temporadasDisponibles.map((season) => (
                <button
                  key={season}
                  className={`btn btn-outline-secondary btn-sm rounded-pill ${selectedSeason === season ? 'active' : ''}`}
                  onClick={() => selectSeason(season)}
                >
                  {season}
                </button>
              )) : aniosDisponibles.map((year) => (
                <button
                  key={year}
                  className={`btn btn-outline-secondary btn-sm rounded-pill ${selectedYear === year ? 'active' : ''}`}
                  onClick={() => selectYear(year)}
                >
                  {year}
                </button>
              ))
            ) : (
              <span className="small text-muted">Primero elegí una competición.</span>
            )}
            {hasCompetition && periodOptions.length === 0 && (
              <span className="small text-muted">No hay opciones disponibles.</span>
            )}
          </div>

          <div className="filter-group mb-3">
            <button
              className={`btn btn-sm rounded-pill ${showFavoritesOnly ? 'btn-warning' : 'btn-outline-warning'}`}
              onClick={() => setShowFavoritesOnly((value) => !value)}
              title="Filtra sobre los partidos ya cargados por los filtros activos"
            >
              ★ Mis partidos {favoritesCount > 0 && `(${favoritesCount})`}
            </button>
            {showFavoritesOnly && !hasActiveServerFilters && (
              <span className="small text-muted">Aplicá un filtro de servidor para cargar partidos favoritos.</span>
            )}
          </div>

          {showStageFilter && (
            <div className="filter-group mb-3">
              <span className="filter-label">Etapa</span>
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
            <div className="filter-group mb-3">
              <span className="filter-label">Grupo</span>
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
            <div className="filter-group">
              <span className="filter-label">Jornada</span>
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
