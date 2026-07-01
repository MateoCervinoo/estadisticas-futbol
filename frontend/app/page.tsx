"use client"

import { useEffect, useMemo, useState } from 'react'
import {
  getPartidoEstadisticas,
  getPartidoPrediccion,
  Partido,
  PartidoEstadisticas,
  PredictionResponse,
} from '../src/services/api'
import FootballLoader from '../components/FootballLoader'
import CalendarDaySelector from './(home)/CalendarDaySelector'
import MatchCard from './(home)/MatchCard'
import MatchDetailModal from './(home)/MatchDetailModal'
import MatchFilters from './(home)/MatchFilters'
import PredictionModal from './(home)/PredictionModal'
import { formatClock, formatDate, groupOf, isPlayed, stageOf, tournamentOf } from './(home)/matchPresentation'
import useFavorites from './(home)/useFavorites'
import useMatches from './(home)/useMatches'
import useMatchFilters from './(home)/useMatchFilters'
import useMatchNotifications from './(home)/useMatchNotifications'

export default function Home() {
  const [now, setNow] = useState<Date>(new Date())
  const [selectedMatch, setSelectedMatch] = useState<Partido | null>(null)
  const [modalMode, setModalMode] = useState<'simulate' | 'detail' | null>(null)
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null)
  const [predLoading, setPredLoading] = useState<boolean>(false)
  const [currentStats, setCurrentStats] = useState<PartidoEstadisticas | null>(null)
  const [statsLoading, setStatsLoading] = useState<boolean>(false)

  const {
    favorites,
    toasts,
    setToasts,
    showFavoritesOnly,
    setShowFavoritesOnly,
    handleToggleFav,
  } = useFavorites()

  const {
    selectedYear,
    setSelectedYear,
    selectedSeason,
    setSelectedSeason,
    selectedDate,
    setSelectedDate,
    competitionFilter,
    setCompetitionFilter,
    stageFilter,
    setStageFilter,
    groupFilter,
    setGroupFilter,
    matchdayFilter,
    setMatchdayFilter,
    showFilters,
    setShowFilters,
    hasActiveServerFilters,
  } = useMatchFilters()

  const activeSeason = isLeagueFilter ? selectedSeason : 'Todos'

  const {
    partidos,
    setPartidos,
    error,
    loading,
    slowLoading,
    initialLoad,
    aniosDisponibles,
    temporadasDisponibles,
    availableDates,
    availableCompetitions,
    availableStages,
    availableGroups,
    availableMatchdays,
  } = useMatches({
    selectedYear,
    selectedSeason: activeSeason,
    selectedDate,
    competitionFilter,
    stageFilter,
    groupFilter,
    matchdayFilter,
    hasActiveServerFilters,
  })

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  useMatchNotifications({
    hasActiveServerFilters,
    selectedYear,
    selectedSeason: activeSeason,
    selectedDate,
    competitionFilter,
    stageFilter,
    groupFilter,
    matchdayFilter,
    setPartidos,
    setToasts,
  })

  const allMatches = partidos ?? []
  const selectedTournament = availableTournaments.find((torneo) => torneo.nombre_canonico === competitionFilter)
  const selectedTournamentType = selectedTournament?.tipo ?? ''
  const competitionOptions = useMemo(
    () => ['Todos', ...Array.from(new Set(availableCompetitions.filter(Boolean)))],
    [availableCompetitions]
  )
  const stageOptions = useMemo(
    () => ['Todos', ...Array.from(new Set(availableStages.filter(Boolean)))],
    [availableStages]
  )
  const groupOptions = useMemo(
    () => ['Todos', ...Array.from(new Set(availableGroups.filter(Boolean)))],
    [availableGroups]
  )
  const matchdayOptions = useMemo(
    () => Array.from(new Set(availableMatchdays)).sort((a, b) => a - b),
    [availableMatchdays]
  )

  const uniqueDates = competitionFilter !== 'Todos' ? availableDates : []

  const showStageFilter = competitionFilter !== 'Todos' && selectedTournamentType !== 'liga' && stageOptions.length > 1
  const showGroupFilter = showStageFilter && (stageFilter === 'Todos' || stageFilter === 'GROUP_STAGE') && groupOptions.length > 1
  const showMatchdayFilter = competitionFilter !== 'Todos' && selectedTournamentType === 'liga' && matchdayOptions.length > 0

  const filteredMatches = allMatches.filter((p) => !showFavoritesOnly || favorites.includes(p.id))

  const openSimulate = (p: Partido) => {
    if (isPlayed(p)) return
    setSelectedMatch(p)
    setPrediction(null)
    setModalMode('simulate')
  }

  const openDetail = (p: Partido) => {
    setSelectedMatch(p)
    setModalMode('detail')
    setCurrentStats(null)
    setStatsLoading(true)
    getPartidoEstadisticas(p.id)
      .then((stats) => setCurrentStats(stats))
      .finally(() => setStatsLoading(false))
  }

  const closeModal = () => {
    setSelectedMatch(null)
    setModalMode(null)
    setPrediction(null)
  }

  // When a simulate modal opens, fetch prediction from backend
  useEffect(() => {
    let mounted = true
    const fetchPrediction = async () => {
      if (!selectedMatch || modalMode !== 'simulate') return
      setPredLoading(true)
      setPrediction(null)
      try {
        if (selectedMatch.fixture_id === null || selectedMatch.fixture_id === undefined) {
          setPrediction({
            status: 'insufficient_data',
            message: 'El partido no tiene fixture_id asociado.',
          })
          return
        }
        const data = await getPartidoPrediccion(selectedMatch.fixture_id)
        if (!mounted) return
        setPrediction(data)
      } catch (err) {
        if (!mounted) return
        setPrediction(null)
      } finally {
        if (mounted) setPredLoading(false)
      }
    }

    fetchPrediction()
    return () => {
      mounted = false
    }
  }, [selectedMatch, modalMode])

  return (
    <main className="min-vh-100 bg-light p-5 text-dark">
      <div className="container mt-4">
        <div className="d-flex align-items-center justify-content-between gap-3 mb-3">
          <div className="d-flex align-items-center gap-3">
            <img src="/pizarron-estadistico.png" alt="Logo Pizarrón Estadístico" className="app-logo" />
          </div>
          <div className="clock-pill text-end">
            <div className="small text-muted">Hoy</div>
            <div className="fw-semibold" suppressHydrationWarning>{formatClock(now)}</div>
          </div>
        </div>
        <hr className="border-top border-secondary mb-5" />

        {error && <div className="alert alert-danger">Error: {error}</div>}

        <section>
          <div className="border rounded-4 bg-white shadow-sm p-3 mb-4">
            <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
              <div>
                <div className="fw-semibold">Calendario</div>
                <div className="small text-muted">Elegí el día para concentrarte en una jornada</div>
              </div>
            </div>

            <CalendarDaySelector
              uniqueDates={uniqueDates}
              selectedDate={selectedDate}
              onSelectDate={setSelectedDate}
            />

            <MatchFilters
              loading={loading}
              hasPartidos={Boolean(partidos)}
              filteredCount={filteredMatches.length}
              showFilters={showFilters}
              setShowFilters={setShowFilters}
              selectedYear={selectedYear}
              setSelectedYear={setSelectedYear}
              selectedSeason={selectedSeason}
              setSelectedSeason={setSelectedSeason}
              aniosDisponibles={aniosDisponibles}
              selectedSeason={selectedSeason}
              setSelectedSeason={setSelectedSeason}
              temporadasDisponibles={temporadasDisponibles}
              showFavoritesOnly={showFavoritesOnly}
              setShowFavoritesOnly={setShowFavoritesOnly}
              favoritesCount={favorites.length}
              hasActiveServerFilters={hasActiveServerFilters}
              competitionOptions={competitionOptions}
              competitionFilter={competitionFilter}
              setCompetitionFilter={setCompetitionFilter}
              isLeagueFilter={isLeagueFilter}
              showStageFilter={showStageFilter}
              stageOptions={stageOptions}
              stageFilter={stageFilter}
              setStageFilter={setStageFilter}
              showGroupFilter={showGroupFilter}
              groupOptions={groupOptions}
              groupFilter={groupFilter}
              setGroupFilter={setGroupFilter}
              showMatchdayFilter={showMatchdayFilter}
              matchdayOptions={matchdayOptions}
              matchdayFilter={matchdayFilter}
              setMatchdayFilter={setMatchdayFilter}
            />
          </div>

          {loading && hasActiveServerFilters && <FootballLoader />}
          {slowLoading && (
            <div className="alert alert-warning">
              La consulta está tardando más de lo esperado. Podés esperar o ajustar los filtros para acotar la búsqueda.
            </div>
          )}

          {!loading && filteredMatches.length === 0 && (
            <div className="text-center py-5">
              {!hasActiveServerFilters ? (
                <>
                  <div className="text-muted fs-5 mb-2">Configurá un filtro para ver partidos</div>
                  <div className="small text-muted">La app no descarga el calendario completo al iniciar</div>
                </>
              ) : initialLoad ? (
                <>
                  <div className="text-muted fs-5 mb-2">Cargando partidos...</div>
                  <div className="small text-muted">Obteniendo datos del servidor</div>
                </>
              ) : (!partidos || partidos.length === 0) ? (
                <>
                  <div className="text-muted fs-5 mb-2">No hay partidos disponibles</div>
                  <div className="small text-muted">Revisá que el CSV histórico y la API estén sincronizados</div>
                </>
              ) : (
                <>
                  <div className="text-muted fs-5 mb-2">No hay partidos con estos filtros</div>
                  <div className="small text-muted">Probá cambiando los filtros</div>
                </>
              )}
            </div>
          )}

          <div className="row">
            {filteredMatches.map((partido) => (
              <MatchCard
                key={partido.id}
                partido={partido}
                isFavorite={favorites.includes(partido.id)}
                onToggleFavorite={handleToggleFav}
                onOpenDetail={openDetail}
                onOpenSimulate={openSimulate}
              />
            ))}
          </div>
        </section>

        {/* Modal */}
        {selectedMatch && (
          <>
            <div className="modal fade show d-block" tabIndex={-1} role="dialog" aria-modal="true" onClick={closeModal}>
              <div className="modal-dialog modal-lg modal-dialog-centered" onClick={(e) => e.stopPropagation()}>
                <div className="modal-content bg-white text-dark border-0 shadow">
                <div className="modal-header bg-light border-bottom border-light">
                  <div>
                    <h2 className="modal-title h5">
                      {tournamentOf(selectedMatch)}
                    </h2>
                    <div className="small text-muted">
                      {stageOf(selectedMatch) ? `${stageOf(selectedMatch)} · ` : ''}{selectedMatch.group ? `${groupOf(selectedMatch)} · ` : ''}{formatDate(selectedMatch.date)}
                    </div>
                  </div>
                    <button type="button" className="btn-close" aria-label="Close" onClick={closeModal} />
                  </div>

                  <div className="modal-body bg-white">
                    {modalMode === 'simulate' ? (
                      <PredictionModal prediction={prediction} predLoading={predLoading} />
                    ) : (
                      <MatchDetailModal selectedMatch={selectedMatch} currentStats={currentStats} statsLoading={statsLoading} />
                    )}
                  </div>

                  <div className="modal-footer bg-light border-top border-light">
                    <button className="btn btn-secondary" onClick={closeModal}>Cerrar</button>
                  </div>
                </div>
              </div>
            </div>
            <div className="modal-backdrop fade show" />
          </>
        )}
      </div>

      {/* Toast notifications */}
      <div style={{ position: 'fixed', bottom: 20, right: 20, zIndex: 9999 }}>
        {toasts.map((t) => (
          <div key={t.id} className="toast show align-items-center text-bg-primary border-0 mb-2" role="alert">
            <div className="d-flex">
              <div className="toast-body small">{t.msg}</div>
              <button type="button" className="btn-close btn-close-white me-2 m-auto" onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))} />
            </div>
          </div>
        ))}
      </div>

    </main>
  )
}
