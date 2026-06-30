"use client"

import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react'
import {
  getPartidos,
  getPartidoEstadisticas,
  getPartidoFilterMetadata,
  getPartidoPrediccion,
  Partido,
  PartidoEstadisticas,
  PredictionResponse,
  WS_URL,
} from '../src/services/api'
import { getFavorites, toggleFavorite } from '../src/services/favorites'
import FootballLoader from '../components/FootballLoader'
import StatRow from '../components/StatRow'

type ExactScore = {
  home: number
  away: number
  prob: number
}

type ProbabilityKey = 'home_win' | 'draw' | 'away_win'

const ARGENTINA_TIME_ZONE = 'America/Argentina/Buenos_Aires'
const DAY_LABEL_FORMAT: Intl.DateTimeFormatOptions = {
  timeZone: ARGENTINA_TIME_ZONE,
  weekday: 'short',
  day: '2-digit',
  month: 'short',
}

const CLOCK_LABEL_FORMAT: Intl.DateTimeFormatOptions = {
  timeZone: ARGENTINA_TIME_ZONE,
  weekday: 'short',
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
}

const TOURNAMENT_LABELS: Record<string, string> = {
  Mundial: 'Mundial',
  Clasificatorias: 'Clasificatorias',
  Amistoso: 'Amistoso',
  'Copa América': 'Copa América',
  Eurocopa: 'Eurocopa',
  'Nations League': 'Nations League',
  Confederaciones: 'Copa Confederaciones',
  'Copa Africana de Naciones': 'Copa Africana',
  'Copa Asiática': 'Copa Asiática',
  'Copa Oro': 'Copa Oro',
  'Juegos Olímpicos': 'Juegos Olímpicos',
  FIFA_WORLD_CUP: 'Mundial',
  WORLD_CUP: 'Mundial',
}

const STAGE_LABELS: Record<string, string> = {
  GROUP_STAGE: 'Fase de Grupos',
  LAST_32: 'Dieciseisavos de Final',
  ROUND_OF_32: 'Dieciseisavos de Final',
  LAST_16: 'Octavos de Final',
  ROUND_OF_16: 'Octavos de Final',
  QUARTER_FINALS: 'Cuartos de Final',
  SEMI_FINALS: 'Semifinales',
  THIRD_PLACE: 'Tercer Puesto',
  FINAL: 'Final',
}

export default function Home() {
  const [partidos, setPartidos] = useState<Partido[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [slowLoading, setSlowLoading] = useState<boolean>(false)
  const [now, setNow] = useState<Date>(new Date())
  const [selectedYear, setSelectedYear] = useState<number | undefined>(undefined)
  const [aniosDisponibles, setAniosDisponibles] = useState<number[]>([])
  const [availableDates, setAvailableDates] = useState<string[]>([])
  const [availableCompetitions, setAvailableCompetitions] = useState<string[]>([])
  const [availableStages, setAvailableStages] = useState<string[]>([])
  const [availableGroups, setAvailableGroups] = useState<string[]>([])
  const [availableMatchdays, setAvailableMatchdays] = useState<number[]>([])
  const [favorites, setFavorites] = useState<number[]>([])
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false)
  const [toasts, setToasts] = useState<{ id: number; msg: string }[]>([])
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [competitionFilter, setCompetitionFilter] = useState<string>('Todos')
  const [stageFilter, setStageFilter] = useState<string>('Todos')
  const [groupFilter, setGroupFilter] = useState<string>('Todos')
  const [matchdayFilter, setMatchdayFilter] = useState<number | undefined>(undefined)
  const [showFilters, setShowFilters] = useState<boolean>(false)
  const [selectedMatch, setSelectedMatch] = useState<Partido | null>(null)
  const [modalMode, setModalMode] = useState<'simulate' | 'detail' | null>(null)
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null)
  const [predLoading, setPredLoading] = useState<boolean>(false)
  const [currentStats, setCurrentStats] = useState<PartidoEstadisticas | null>(null)
  const [statsLoading, setStatsLoading] = useState<boolean>(false)
  const [initialLoad, setInitialLoad] = useState<boolean>(true)

  const hasActiveServerFilters = Boolean(
    selectedYear !== undefined
    || selectedDate
    || competitionFilter !== 'Todos'
    || stageFilter !== 'Todos'
    || groupFilter !== 'Todos'
    || matchdayFilter !== undefined
  )

  useEffect(() => {
    getPartidoFilterMetadata()
      .then((metadata) => {
        setAniosDisponibles(metadata.years)
        setAvailableDates(metadata.dates)
        setAvailableCompetitions(metadata.tournaments)
        setAvailableStages(metadata.stages)
        setAvailableGroups(metadata.groups)
        setAvailableMatchdays(metadata.matchdays)
      })
      .catch(() => {})
    setFavorites(getFavorites())
  }, [])

  useEffect(() => {
    if (!hasActiveServerFilters) {
      setPartidos(null)
      setLoading(false)
      setSlowLoading(false)
      setError(null)
      setInitialLoad(false)
      return
    }

    let mounted = true
    let slowTimer: ReturnType<typeof setTimeout> | undefined
    setLoading(true)
    setSlowLoading(false)
    setError(null)
    slowTimer = setTimeout(() => {
      if (mounted) setSlowLoading(true)
    }, 6000)

    getPartidos({
      year: selectedYear,
      date: selectedDate ?? undefined,
      tournament: competitionFilter !== 'Todos' ? competitionFilter : undefined,
      stage: stageFilter !== 'Todos' ? stageFilter : undefined,
      group: groupFilter !== 'Todos' ? groupFilter : undefined,
      matchday: matchdayFilter,
    })
      .then((data) => {
        if (mounted) {
          setPartidos(data)
          setInitialLoad(false)
        }
      })
      .catch((err) => {
        if (mounted) {
          setError(String(err))
          setInitialLoad(false)
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false)
          setSlowLoading(false)
        }
        if (slowTimer) clearTimeout(slowTimer)
      })

    return () => {
      mounted = false
      if (slowTimer) clearTimeout(slowTimer)
    }
  }, [selectedYear, selectedDate, competitionFilter, stageFilter, groupFilter, matchdayFilter, hasActiveServerFilters])

  useEffect(() => {
    getPartidoFilterMetadata({
      year: selectedYear,
      tournament: competitionFilter !== 'Todos' ? competitionFilter : undefined,
      stage: stageFilter !== 'Todos' ? stageFilter : undefined,
    })
      .then((metadata) => {
        setAvailableStages(metadata.stages)
        setAvailableGroups(metadata.groups)
        setAvailableMatchdays(metadata.matchdays)
      })
      .catch(() => {})
  }, [selectedYear, competitionFilter, stageFilter])

  useEffect(() => {
    setStageFilter('Todos')
    setGroupFilter('Todos')
    setMatchdayFilter(undefined)
  }, [competitionFilter])

  useEffect(() => {
    if (stageFilter !== 'Todos' && stageFilter !== 'GROUP_STAGE') {
      setGroupFilter('Todos')
    }
  }, [stageFilter])

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  // Auto-dismiss toasts after 5s
  useEffect(() => {
    if (toasts.length === 0) return
    const t = setTimeout(() => setToasts((prev) => prev.slice(1)), 5000)
    return () => clearTimeout(t)
  }, [toasts])

  const handleToggleFav = useCallback((partidoId: number) => {
    const nowFav = toggleFavorite(partidoId)
    setFavorites(getFavorites())
    if (nowFav) {
      setToasts((prev) => [...prev, { id: Date.now(), msg: 'Agregado a Mis Partidos' }])
    }
  }, [])

  // WebSocket connection to re-fetch on live notifications
  const matchFiltersRef = useRef({
    hasActiveServerFilters,
    selectedYear,
    selectedDate,
    competitionFilter,
    stageFilter,
    groupFilter,
    matchdayFilter,
  })

  useEffect(() => {
    matchFiltersRef.current = {
      hasActiveServerFilters,
      selectedYear,
      selectedDate,
      competitionFilter,
      stageFilter,
      groupFilter,
      matchdayFilter,
    }
  }, [hasActiveServerFilters, selectedYear, selectedDate, competitionFilter, stageFilter, groupFilter, matchdayFilter])

  useEffect(() => {
    let ws: WebSocket | null = null
    let reconnectTimer: ReturnType<typeof setTimeout>
    let cancelled = false

    const connect = () => {
      if (cancelled) return
      ws = new WebSocket(WS_URL)
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'notification') {
            const filters = matchFiltersRef.current
            if (!filters.hasActiveServerFilters) return
            getPartidos({
              year: filters.selectedYear,
              date: filters.selectedDate ?? undefined,
              tournament: filters.competitionFilter !== 'Todos' ? filters.competitionFilter : undefined,
              stage: filters.stageFilter !== 'Todos' ? filters.stageFilter : undefined,
              group: filters.groupFilter !== 'Todos' ? filters.groupFilter : undefined,
              matchday: filters.matchdayFilter,
            }).then((data) => {
              if (data) setPartidos(data)
            }).catch(() => {})
            const pid = Number(msg.data?.partido_id)
            if (pid && getFavorites().includes(pid)) {
              setToasts((prev) => [...prev, { id: Date.now(), msg: `⭐ ${msg.data.mensaje}` }])
            } else if (pid) {
              setToasts((prev) => [...prev, { id: Date.now(), msg: msg.data.mensaje }])
            }
          }
        } catch {}
      }
      ws.onclose = () => {
        if (!cancelled) reconnectTimer = setTimeout(connect, 5000)
      }
      ws.onerror = () => {
        ws?.close()
      }
    }

    connect()
    return () => {
      cancelled = true
      if (ws?.readyState === WebSocket.CONNECTING) {
        ws.onopen = () => ws?.close()
      } else {
        ws?.close()
      }
      clearTimeout(reconnectTimer)
    }
  }, [WS_URL])

  const formatScore = (s: number | null) => (s === null || s === undefined ? '-' : String(s))
  const parseMatchDate = (iso: string) => {
    const value = String(iso ?? '').trim()
    if (!value) return new Date(Number.NaN)
    const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(value)
    return new Date(hasTimezone ? value : `${value}Z`)
  }
  const formatDate = (iso: string) => {
    try {
      return parseMatchDate(iso).toLocaleString('es-AR', {
        timeZone: ARGENTINA_TIME_ZONE,
        weekday: 'short',
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return iso
    }
  }
  const formatDateLabel = (iso: string) => {
    try {
      return parseMatchDate(iso).toLocaleDateString('es-AR', DAY_LABEL_FORMAT)
    } catch {
      return iso
    }
  }

  const formatClock = (date: Date) => {
    try {
      return date.toLocaleString('es-AR', CLOCK_LABEL_FORMAT)
    } catch {
      return date.toISOString()
    }
  }

  const dateKey = (iso: string) => {
    try {
      const parts = new Intl.DateTimeFormat('en-CA', {
        timeZone: ARGENTINA_TIME_ZONE,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      }).formatToParts(parseMatchDate(iso))

      const year = parts.find((part) => part.type === 'year')?.value
      const month = parts.find((part) => part.type === 'month')?.value
      const day = parts.find((part) => part.type === 'day')?.value

      return year && month && day ? `${year}-${month}-${day}` : iso.slice(0, 10)
    } catch {
      return iso.slice(0, 10)
    }
  }

  const isPlayed = (p: Partido) => {
    if (['NS', 'TIMED', 'SCHEDULED', 'IN_PLAY', 'PAUSED'].includes(p.status)) return false
    const hasScore = p.home_score !== null && p.home_score !== undefined && p.away_score !== null && p.away_score !== undefined
    return hasScore || ['FT', 'AET', 'PEN'].includes(p.status)
  }

  const tournamentOf = (p: Partido) => {
    const rawTournament = p.tournament?.trim()
    if (!rawTournament) return 'Desconocido'
    return TOURNAMENT_LABELS[rawTournament] ?? rawTournament
  }

  const stageOf = (p: Partido) => {
    const rawStage = p.stage?.trim()
    if (!rawStage) return ''
    return STAGE_LABELS[rawStage] ?? rawStage
  }

  const groupOf = (p: Partido) => {
    const rawGroup = p.group?.trim()
    if (!rawGroup) return 'Sin grupo'
    return rawGroup.replace('GROUP_', 'Grupo ')
  }

  const topExactScores = (predictionData: PredictionResponse | null): ExactScore[] => {
    if (Array.isArray(predictionData?.score_matrix_flat)) {
      return predictionData.score_matrix_flat
        .filter((item) => Number.isFinite(Number(item?.prob)))
        .map((item) => ({
          home: Number(item.home),
          away: Number(item.away),
          prob: Number(item.prob),
        }))
        .sort((a: ExactScore, b: ExactScore) => b.prob - a.prob)
        .slice(0, 3)
    }

    if (!Array.isArray(predictionData?.score_matrix)) return []

    return predictionData.score_matrix
      .flatMap((row: number[], home: number) =>
        Array.isArray(row)
          ? row.map((prob: number, away: number) => ({
              home,
              away,
              prob: Number(prob),
            }))
          : []
      )
      .filter((item: ExactScore) => Number.isFinite(item.prob))
      .sort((a: ExactScore, b: ExactScore) => b.prob - a.prob)
      .slice(0, 3)
  }

  const exactScoreMatrix = (predictionData: PredictionResponse | null): number[][] => {
    if (!Array.isArray(predictionData?.score_matrix)) return []

    return predictionData.score_matrix.slice(0, 5).map((row) =>
      Array.isArray(row)
        ? row.slice(0, 5).map((cell) => {
            const value = Number(cell)
            return Number.isFinite(value) ? value : 0
          })
        : []
    )
  }

  const heatmapClass = (value: number, maxValue: number) => {
    if (maxValue <= 0 || value <= 0) return 'bg-white'

    const intensity = value / maxValue
    if (intensity >= 0.66) return 'bg-success text-white fw-bold'
    if (intensity >= 0.33) return 'bg-warning text-dark fw-semibold'
    return 'bg-danger text-white'
  }

  const rawStageLabel = (stage: string) => STAGE_LABELS[stage] ?? stage
  const rawGroupLabel = (group: string) => group.replace('GROUP_', 'Grupo ')

  const dedupeMatches = (matches: Partido[]) => {
    const byKey = new Map<string, Partido>()
    for (const match of matches) {
      const key = [
        dateKey(match.date),
        (match.home_team || '').trim().toLowerCase(),
        (match.away_team || '').trim().toLowerCase(),
        tournamentOf(match).trim().toLowerCase(),
      ].join('|')
      const current = byKey.get(key)
      if (!current) {
        byKey.set(key, match)
        continue
      }

      const currentIsApi = current.fixture_id !== null && current.fixture_id !== undefined
      const nextIsApi = match.fixture_id !== null && match.fixture_id !== undefined
      if ((!currentIsApi && nextIsApi) || (match.home_crest_url && !current.home_crest_url)) {
        byKey.set(key, match)
      }
    }
    return Array.from(byKey.values())
  }

  const allMatches = useMemo(() => dedupeMatches(partidos ?? []), [partidos])
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

  const uniqueDates = availableDates

  const selectedCompetitionLabel = competitionFilter === 'Todos'
    ? ''
    : (TOURNAMENT_LABELS[competitionFilter] ?? competitionFilter)
  const isWorldCupFilter = selectedCompetitionLabel === 'Mundial' || /world cup/i.test(competitionFilter)
  const isQualifierFilter = /clasific|qualification|qualifier/i.test(selectedCompetitionLabel) || /qualification|qualifier/i.test(competitionFilter)
  const isLeagueFilter = competitionFilter !== 'Todos' && !isWorldCupFilter && !isQualifierFilter
  const showStageFilter = isWorldCupFilter
  const showGroupFilter = isWorldCupFilter && (stageFilter === 'Todos' || stageFilter === 'GROUP_STAGE')
  const showMatchdayFilter = isLeagueFilter && matchdayOptions.length > 0

  // map team names to flag-icon two-letter codes (extend as needed)
  const teamToFlag: Record<string, string> = {
    Argentina: 'ar',
    Brazil: 'br',
    France: 'fr',
    Iceland: 'is',
    Spain: 'es',
    Germany: 'de',
    Uruguay: 'uy',
    'South Korea': 'kr',
  }

  const flagClass = (team: string, explicitCode?: string | null) => {
    const code = (explicitCode || teamToFlag[team] || team.slice(0, 2)).toLowerCase()
    return `fi fi-${code}`
  }

  const probabilityBarClass = (key: ProbabilityKey) => {
    if (key === 'home_win') return 'bg-success'
    if (key === 'draw') return 'bg-warning text-dark'
    return 'bg-danger'
  }

  const topScoreBadgeClass = (index: number) => {
    if (index === 0) return 'bg-success'
    if (index === 1) return 'bg-warning text-dark'
    return 'bg-danger'
  }

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
    getPartidoEstadisticas(p.id).then((stats) => {
      setCurrentStats(stats)
      setStatsLoading(false)
    })
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
      try {
        if (selectedMatch.fixture_id === null || selectedMatch.fixture_id === undefined) return
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

            <div className="day-selector d-flex gap-2 overflow-auto pb-2">
              {uniqueDates.length === 0 && <div className="text-muted">No hay días cargados</div>}
              {uniqueDates.map((iso) => {
                const active = selectedDate === iso
                const label = formatDateLabel(`${iso}T12:00:00Z`)

                return (
                  <button
                    key={iso}
                    className={`btn day-selector-btn text-start ${active ? 'btn-primary' : 'btn-outline-secondary'}`}
                    onClick={() => setSelectedDate(active ? null : iso)}
                  >
                    <div className="small text-uppercase opacity-75">Día</div>
                    <div className="fw-semibold text-nowrap">{label}</div>
                  </button>
                )
              })}
            </div>

            <div className="border-top mt-3 pt-3">
              <div className="d-flex align-items-center justify-content-between gap-2">
                <div>
                  <div className="fw-semibold">Filtros</div>
                  <div className="small text-muted">Filtrá por año, competencia y opciones propias del torneo</div>
                </div>
                <div className="d-flex align-items-center gap-2">
                  {!loading && partidos && (
                    <span className="badge bg-secondary rounded-pill">{filteredMatches.length} partidos</span>
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
                      onClick={() => setShowFavoritesOnly((v) => !v)}
                      title="Filtra sobre los partidos ya cargados por los filtros activos"
                    >
                      ⭐ Mis Partidos {favorites.length > 0 && `(${favorites.length})`}
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
            {filteredMatches.map((p) => {
              const played = isPlayed(p)

              return (
                <div key={p.id} className="col-12 col-md-6 mb-3">
                  <div className="card bg-white text-dark shadow-sm border-0 rounded-3 mb-3 p-4 h-100">
                    <div className="d-flex justify-content-between align-items-start gap-3">
                      <div className="small text-muted d-flex align-items-center gap-2">
                        <span
                          role="button"
                          className={`${favorites.includes(p.id) ? 'text-warning' : 'text-muted'}`}
                          onClick={() => handleToggleFav(p.id)}
                          style={{ cursor: 'pointer', fontSize: '1rem' }}
                          title={favorites.includes(p.id) ? 'Quitar de favoritos' : 'Agregar a favoritos'}
                        >
                          {favorites.includes(p.id) ? '★' : '☆'}
                        </span>
                        {tournamentOf(p)}{stageOf(p) ? ` · ${stageOf(p)}` : ''}{p.group ? ` · ${groupOf(p)}` : ''}
                        {p.status === 'IN_PLAY' && (
                          <span className="badge bg-danger rounded-pill live-pulse small">EN VIVO</span>
                        )}
                      </div>
                      <div className="small text-muted text-end">{formatDate(p.date)}</div>
                    </div>

                    <div className="d-flex align-items-center justify-content-between gap-3 mt-3">
                      <div className="d-flex align-items-center flex-fill">
                        {p.home_crest_url ? (
                          <img src={p.home_crest_url} alt={`Escudo ${p.home_team}`} width={22} height={22} className="me-2" />
                        ) : (
                          <span className={`${flagClass(p.home_team, p.home_codigo_bandera)} me-2`} />
                        )}
                        <div className="fw-semibold">{p.home_team}</div>
                      </div>

                      <div className="text-center">
                        {played ? (
                          <div className="fs-4 fw-bold">{formatScore(p.home_score)} - {formatScore(p.away_score)}</div>
                        ) : (
                          <div className="text-muted">vs</div>
                        )}
                      </div>

                      <div className="d-flex align-items-center justify-content-end flex-fill">
                        <div className="fw-semibold text-end me-2">{p.away_team}</div>
                        {p.away_crest_url ? (
                          <img src={p.away_crest_url} alt={`Escudo ${p.away_team}`} width={22} height={22} className="ms-2" />
                        ) : (
                          <span className={`${flagClass(p.away_team, p.away_codigo_bandera)} ms-2`} />
                        )}
                      </div>
                    </div>

                    <div className="mt-3 d-flex justify-content-end">
                      {played ? (
                        <button className="btn btn-outline-secondary rounded-pill" onClick={() => openDetail(p)}>Ver detalle</button>
                      ) : (
                        <button className="btn btn-success rounded-pill" onClick={() => openSimulate(p)}>Simular</button>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
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
                      <div>
                        <div className="border-bottom border-light pb-3 mb-3">
                          <div className="fw-semibold mb-2">Probabilidades</div>
                          {predLoading && <div className="text-muted small">Calculando probabilidades...</div>}
                          {!predLoading && prediction && (
                            <div className="vstack gap-3">
                              {([
                                { key: 'home_win' as const, label: 'Local', value: Number(prediction.home_win ?? 0) },
                                { key: 'draw' as const, label: 'Empate', value: Number(prediction.draw ?? 0) },
                                { key: 'away_win' as const, label: 'Visitante', value: Number(prediction.away_win ?? 0) },
                              ]).map((item) => {
                                const barClass = probabilityBarClass(item.key)
                                return (
                                  <div key={item.key}>
                                    <div className="d-flex justify-content-between small mb-1">
                                      <span className="fw-semibold">{item.label}</span>
                                      <span>{item.value}%</span>
                                    </div>
                                    <div className="progress" role="progressbar" aria-valuenow={item.value} aria-valuemin={0} aria-valuemax={100}>
                                      <div className={`progress-bar ${barClass}`} style={{ width: `${item.value}%` }} />
                                    </div>
                                  </div>
                                )
                              })}
                            </div>
                          )}
                          {!predLoading && !prediction && (
                            <div className="text-muted small">No hay predicción disponible.</div>
                          )}
                        </div>

                        {!predLoading && prediction?.score_matrix && (
                          <div>
                            <div className="fw-semibold mb-2">Top 3 resultados posibles</div>
                            <div className="d-flex flex-wrap gap-2">
                              {topExactScores(prediction).map((score, index) => (
                                <span key={`${score.home}-${score.away}`} className={`badge ${topScoreBadgeClass(index)} text-wrap fs-6`}>
                                  {score.home}-{score.away} - {score.prob}%
                                </span>
                              ))}
                            </div>

                            <hr className="text-muted" />

                            <h6 className="text-muted fw-semibold mb-2">Matriz de Resultados Posibles (%)</h6>
                            {(() => {
                              const matrix = exactScoreMatrix(prediction)
                              const maxValue = Math.max(...matrix.flat(), 0)

                              return (
                                <div className="table-responsive">
                                  <div className="d-flex justify-content-between small text-muted mb-2 px-1">
                                    <span>Filas: Local</span>
                                    <span>Columnas: Visitante</span>
                                  </div>
                                  <table className="table table-bordered table-sm text-center align-middle mb-0">
                                    <thead className="table-light">
                                      <tr>
                                        <th scope="col" className="small text-muted">Marcador</th>
                                        {[0, 1, 2, 3, 4].map((goals) => (
                                          <th key={`away-${goals}`} scope="col">
                                            {goals === 4 ? '4+' : goals}
                                          </th>
                                        ))}
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {matrix.map((row, homeGoals) => (
                                        <tr key={`home-${homeGoals}`}>
                                          <th scope="row" className="table-light">
                                            {homeGoals === 4 ? '4+' : homeGoals}
                                          </th>
                                          {[0, 1, 2, 3, 4].map((awayGoals) => {
                                            const value = row[awayGoals] ?? 0

                                            return (
                                              <td key={`${homeGoals}-${awayGoals}`} className={heatmapClass(value, maxValue)}>
                                                {value}%
                                              </td>
                                            )
                                          })}
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              )
                            })()}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div>
                          <div className="border-bottom border-light pb-3 mb-3">
                            <div className="d-flex align-items-center justify-content-between gap-3">
                              <div className="d-flex align-items-center gap-2">
                                <span className={`${flagClass(selectedMatch.home_team, selectedMatch.home_codigo_bandera)}`} />
                                <div>
                                  <div className="fw-semibold">{selectedMatch.home_team}</div>
                                  <div className="small text-muted">Local</div>
                                </div>
                              </div>

                              <div className="text-center">
                                <div className="fw-bold fs-4">{formatScore(selectedMatch.home_score)} - {formatScore(selectedMatch.away_score)}</div>
                                {(selectedMatch.ht_home_score != null || selectedMatch.ht_away_score != null) && (
                                  <div className="small text-muted">HT: {formatScore(selectedMatch.ht_home_score)} - {formatScore(selectedMatch.ht_away_score)}</div>
                                )}
                              </div>

                              <div className="d-flex align-items-center gap-2 text-end">
                                <div>
                                  <div className="fw-semibold">{selectedMatch.away_team}</div>
                                  <div className="small text-muted">Visitante</div>
                                </div>
                                <span className={`${flagClass(selectedMatch.away_team, selectedMatch.away_codigo_bandera)}`} />
                              </div>
                            </div>
                          </div>

                          {statsLoading && <div className="text-muted small text-center py-3">Cargando estadísticas...</div>}

                          {!statsLoading && currentStats && (
                            <div>
                              <div className="fw-semibold mb-2">Estadísticas</div>
                              <div className="vstack gap-2">
                                {currentStats.xg_local != null && currentStats.xg_visitante != null && (
                                  <StatRow label="xG" home={currentStats.xg_local} away={currentStats.xg_visitante} fmt="float" />
                                )}
                                {currentStats.remates_local != null && (
                                  <StatRow label="Remates" home={currentStats.remates_local} away={currentStats.remates_visitante} />
                                )}
                                {currentStats.remates_puerta_local != null && (
                                  <StatRow label="Remates a puerta" home={currentStats.remates_puerta_local} away={currentStats.remates_puerta_visitante} />
                                )}
                                {currentStats.posesion_local != null && (
                                  <StatRow label="Posesión" home={currentStats.posesion_local} away={currentStats.posesion_visitante} fmt="pct" />
                                )}
                                {currentStats.corners_local != null && (
                                  <StatRow label="Córners" home={currentStats.corners_local} away={currentStats.corners_visitante} />
                                )}
                                {currentStats.faltas_local != null && (
                                  <StatRow label="Faltas" home={currentStats.faltas_local} away={currentStats.faltas_visitante} />
                                )}
                                {currentStats.tarjetas_amarillas_local != null && (
                                  <StatRow label="Amarillas" home={currentStats.tarjetas_amarillas_local} away={currentStats.tarjetas_amarillas_visitante} />
                                )}
                                {currentStats.tarjetas_rojas_local != null && (
                                  <StatRow label="Rojas" home={currentStats.tarjetas_rojas_local} away={currentStats.tarjetas_rojas_visitante} />
                                )}
                                {currentStats.fueras_juego_local != null && (
                                  <StatRow label="Fueras de juego" home={currentStats.fueras_juego_local} away={currentStats.fueras_juego_visitante} />
                                )}
                                {currentStats.paradas_local != null && (
                                  <StatRow label="Paradas" home={currentStats.paradas_local} away={currentStats.paradas_visitante} />
                                )}
                              </div>
                            </div>
                          )}

                          {!statsLoading && !currentStats && (
                            <div className="small text-muted text-center py-3">
                              Estadísticas avanzadas no disponibles para este partido.
                            </div>
                          )}
                      </div>
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
