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
    isLeagueFilter,
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
    availableTournaments,
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
  const liveMatches = allMatches.filter((p) => p.status === 'IN_PLAY')
  const upcomingMatches = allMatches.filter((p) => !isPlayed(p) && p.status !== 'IN_PLAY')
  const playedMatches = allMatches.filter(isPlayed)
  const featuredMatch = liveMatches[0] ?? upcomingMatches[0] ?? filteredMatches[0]

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
    <main className="home-shell min-vh-100 text-dark">
      <div className="container py-4 py-lg-5">
        <section className="home-hero mb-4">
          <div className="row g-4 align-items-center">
            <div className="col-lg-7">
              <span className="app-eyebrow">Match command center</span>
              <h1 className="display-5 fw-black mb-3">Calendario inteligente para decidir qué partido mirar.</h1>
              <p className="home-hero-copy mb-4">
                Priorizá vivos, próximos y favoritos con filtros de torneo listos para análisis, exportación y vistas guardadas.
              </p>
              <div className="d-flex flex-wrap gap-2">
                <span className="hero-chip danger">{liveMatches.length} en vivo</span>
                <span className="hero-chip success">{upcomingMatches.length} próximos</span>
                <span className="hero-chip warning">{favorites.length} favoritos</span>
                <span className="hero-chip muted">{playedMatches.length} finalizados</span>
              </div>
            </div>
            <div className="col-lg-5">
              <div className="hero-control-card">
                <div className="d-flex align-items-center justify-content-between gap-3 mb-3">
                  <img src="/pizarron-estadistico.png" alt="Logo Pizarrón Estadístico" className="app-logo compact" />
                  <div className="clock-pill text-end">
                    <div className="small text-muted">Ahora</div>
                    <div className="fw-semibold" suppressHydrationWarning>{formatClock(now)}</div>
                  </div>
                </div>
                <div className="featured-match-card">
                  <div className="small text-muted mb-1">Partido destacado</div>
                  {featuredMatch ? (
                    <>
                      <div className="fw-bold text-truncate">{featuredMatch.home_team} vs {featuredMatch.away_team}</div>
                      <div className="small text-muted text-truncate">{tournamentOf(featuredMatch)} · {formatDate(featuredMatch.date)}</div>
                    </>
                  ) : (
                    <div className="text-muted small">Aplicá filtros para cargar una agenda destacada.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>

        {error && (
          <div className="app-alert app-alert-danger mb-4">
            <strong>No pudimos cargar el calendario.</strong>
            <span>{error}</span>
            <small>Revisá que la API esté activa o probá acotar los filtros.</small>
          </div>
        )}

        <section>
          <div className="app-surface p-3 p-lg-4 mb-4">
            <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
              <div>
                <span className="app-eyebrow dark">Calendario</span>
                <h2 className="h4 fw-bold mb-1">Explorá por torneo, día y contexto</h2>
                <div className="small text-muted">Elegí una competición para activar días, fases y jornadas disponibles.</div>
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
            <div className="app-alert app-alert-warning">
              <strong>La consulta está tardando más de lo esperado.</strong>
              <span>Podés esperar o ajustar torneo, temporada o fase para acotar la búsqueda.</span>
            </div>
          )}

          {!loading && filteredMatches.length === 0 && (
            <div className="app-empty-state my-4">
              {!hasActiveServerFilters ? (
                <>
                  <strong>Configurá un filtro para ver partidos</strong>
                  <span>La app evita descargar todo el calendario al iniciar. Elegí competición y período para empezar.</span>
                </>
              ) : initialLoad ? (
                <>
                  <strong>Cargando partidos...</strong>
                  <span>Obteniendo datos del servidor.</span>
                </>
              ) : (!partidos || partidos.length === 0) ? (
                <>
                  <strong>No hay partidos disponibles</strong>
                  <span>Revisá que el histórico y la API estén sincronizados para esta combinación.</span>
                </>
              ) : (
                <>
                  <strong>No hay partidos con estos filtros</strong>
                  <span>Probá quitar favoritos, cambiar etapa o ampliar el período.</span>
                </>
              )}
            </div>
          )}

          <div className="row g-3">
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
