"use client"

import React, { useEffect, useMemo, useState } from 'react'
import { getPartidos, Partido } from '../src/services/api'

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
  GROUP_STAGE: 'Fase de Grupos',
  ROUND_OF_16: 'Octavos de Final',
  QUARTER_FINALS: 'Cuartos de Final',
  SEMI_FINALS: 'Semifinales',
  THIRD_PLACE: 'Tercer Puesto',
  FINAL: 'Final',
  FIFA_WORLD_CUP: 'Mundial',
  WORLD_CUP: 'Mundial',
}

const STAGE_LABELS: Record<string, string> = {
  GROUP_STAGE: 'Fase de Grupos',
  ROUND_OF_16: 'Octavos de Final',
  QUARTER_FINALS: 'Cuartos de Final',
  SEMI_FINALS: 'Semifinales',
  THIRD_PLACE: 'Tercer Puesto',
  FINAL: 'Final',
}

export default function Home() {
  const [partidos, setPartidos] = useState<Partido[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  // start in loading state so the initial render shows a loading message
  const [loading, setLoading] = useState<boolean>(true)
  const [now, setNow] = useState<Date>(new Date())

  useEffect(() => {
    let mounted = true
    setLoading(true)
    getPartidos()
      .then((data) => {
        if (mounted) setPartidos(data)
      })
      .catch((err) => {
        if (mounted) setError(String(err))
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })

    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

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
    const hasScore = p.home_score !== null && p.home_score !== undefined && p.away_score !== null && p.away_score !== undefined
    return hasScore || ['FT', 'AET', 'PEN'].includes(p.status)
  }

  const tournamentOf = (p: Partido) => {
    const rawTournament = p.tournament?.trim()
    if (!rawTournament) return 'Mundial'
    return TOURNAMENT_LABELS[rawTournament] ?? rawTournament
  }

  const stageOf = (p: Partido) => {
    const rawStage = p.stage?.trim()
    if (!rawStage) return 'Sin etapa'
    return STAGE_LABELS[rawStage] ?? rawStage
  }

  const groupOf = (p: Partido) => {
    const rawGroup = p.group?.trim()
    if (!rawGroup) return 'Sin grupo'
    return rawGroup.replace('GROUP_', 'Grupo ')
  }

  const topExactScores = (predictionData: any): ExactScore[] => {
    if (Array.isArray(predictionData?.score_matrix_flat)) {
      return predictionData.score_matrix_flat
        .filter((item: any) => Number.isFinite(Number(item?.prob)))
        .map((item: any) => ({
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

  const exactScoreMatrix = (predictionData: any): number[][] => {
    if (!Array.isArray(predictionData?.score_matrix)) return []

    return predictionData.score_matrix.slice(0, 5).map((row: any[]) =>
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

  // UI states for filters and modals
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [competitionFilter, setCompetitionFilter] = useState<string>('Todos')
  const [stageFilter, setStageFilter] = useState<string>('Todos')
  const [groupFilter, setGroupFilter] = useState<string>('Todos')
  const [showFilters, setShowFilters] = useState<boolean>(false)
  // single selectedMatch controls any open modal; modalMode decides which modal to show
  const [selectedMatch, setSelectedMatch] = useState<Partido | null>(null)
  const [modalMode, setModalMode] = useState<'simulate' | 'detail' | null>(null)
  const [prediction, setPrediction] = useState<any | null>(null)
  const [predLoading, setPredLoading] = useState<boolean>(false)

  const allMatches = partidos ?? []
  const competitionOptions = useMemo(
    () => ['Todos', ...Array.from(new Set(allMatches.map(tournamentOf).filter(Boolean)))],
    [allMatches]
  )
  const stageOptions = useMemo(
    () => ['Todos', ...Array.from(new Set(allMatches.map(stageOf).filter(Boolean)))],
    [allMatches]
  )
  const groupOptions = useMemo(
    () => ['Todos', ...Array.from(new Set(allMatches.map(groupOf).filter((g) => g && g !== 'Sin grupo')))],
    [allMatches]
  )

  // build a list of unique dates for the calendar bar based on every match, including past days
  const uniqueDates = Array.from(
    new Set(allMatches.map((p) => dateKey(p.date)))
  ).sort()

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

  const filteredMatches = allMatches.filter((p) => {
    const matchesDate = !selectedDate || dateKey(p.date) === selectedDate
    const matchesCompetition = !competitionFilter || competitionFilter === 'Todos' || tournamentOf(p) === competitionFilter
    const matchesStage = !stageFilter || stageFilter === 'Todos' || stageOf(p) === stageFilter
    const matchesGroup = !groupFilter || groupFilter === 'Todos' || groupOf(p) === groupFilter

    return matchesDate && matchesCompetition && matchesStage && matchesGroup
  })

  const openSimulate = (p: Partido) => {
    if (isPlayed(p)) return
    setSelectedMatch(p)
    setPrediction(null)
    setModalMode('simulate')
  }

  const openDetail = (p: Partido) => {
    setSelectedMatch(p)
    setModalMode('detail')
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
        // Use explicit backend base URL so client fetches hit the FastAPI server
        const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
        const res = await fetch(`${baseUrl}/api/partidos/${selectedMatch.fixture_id}/prediccion`)
        if (!mounted) return
        if (!res.ok) {
          setPrediction(null)
          setPredLoading(false)
          return
        }
        const data = await res.json()
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

        {/* Loading / Error */}
        {(loading || partidos === null) && <div className="text-center text-muted py-4">Cargando partidos...</div>}
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
                  <div className="small text-muted">Filtrá por competencia, etapa o grupo</div>
                </div>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-secondary d-flex align-items-center gap-2"
                  onClick={() => setShowFilters((value) => !value)}
                >
                  <span>{showFilters ? 'Ocultar' : 'Mostrar'}</span>
                  <span aria-hidden="true">{showFilters ? '▴' : '▾'}</span>
                </button>
              </div>

              {showFilters && (
                <div className="pt-3">
                  <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
                    <span className="small text-muted">Competición:</span>
                    {competitionOptions.map((opt) => (
                      <button
                        key={opt}
                        className={`btn btn-outline-secondary btn-sm rounded-pill ${competitionFilter === opt ? 'active' : ''}`}
                        onClick={() => setCompetitionFilter(opt)}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>

                  <div className="d-flex flex-wrap align-items-center gap-2 mb-3">
                    <span className="small text-muted">Etapa:</span>
                    {stageOptions.map((opt) => (
                      <button
                        key={`stage-${opt}`}
                        className={`btn btn-outline-secondary btn-sm rounded-pill ${stageFilter === opt ? 'active' : ''}`}
                        onClick={() => setStageFilter(opt)}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>

                  <div className="d-flex flex-wrap align-items-center gap-2">
                    <span className="small text-muted">Grupo:</span>
                    {groupOptions.map((opt) => (
                      <button
                        key={`group-${opt}`}
                        className={`btn btn-outline-secondary btn-sm rounded-pill ${groupFilter === opt ? 'active' : ''}`}
                        onClick={() => setGroupFilter(opt)}
                      >
                        {opt}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="row">
            {filteredMatches.map((p) => {
              const played = isPlayed(p)

              return (
                <div key={p.id} className="col-12 col-md-6 mb-3">
                  <div className="card bg-white text-dark shadow-sm border-0 rounded-3 mb-3 p-4 h-100">
                    <div className="d-flex justify-content-between align-items-start gap-3">
                      <div className="small text-muted">{tournamentOf(p)} · {stageOf(p)}{p.group ? ` · ${groupOf(p)}` : ''}</div>
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
                      {stageOf(selectedMatch)}{selectedMatch.group ? ` · ${groupOf(selectedMatch)}` : ''} - {formatDate(selectedMatch.date)}
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

                          <div className="small text-muted">
                            Estadísticas avanzadas (posesión, remates y faltas) no disponibles en este momento.
                          </div>
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
    </main>
  )
}
