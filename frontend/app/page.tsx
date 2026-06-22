"use client"

import React, { useEffect, useState } from 'react'
import { getPartidos, Partido } from '../src/services/api'

export default function Home() {
  const [partidos, setPartidos] = useState<Partido[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  // start in loading state so the initial render shows a loading message
  const [loading, setLoading] = useState<boolean>(true)

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

  const formatXG = (x: number | null) => (x === null || x === undefined ? '-' : x.toFixed(2))
  const formatScore = (s: number | null) => (s === null || s === undefined ? '-' : String(s))
  const formatDate = (iso: string) => {
    try {
      const d = new Date(iso)
      return d.toLocaleString(undefined, {
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
  // UI states for tabs, filters and modals
  const [tab, setTab] = useState<'upcoming' | 'results'>('upcoming')
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const [competitionFilter, setCompetitionFilter] = useState<string>('Todos')
  // single selectedMatch controls any open modal; modalMode decides which modal to show
  const [selectedMatch, setSelectedMatch] = useState<Partido | null>(null)
  const [modalMode, setModalMode] = useState<'simulate' | 'detail' | null>(null)

  // derive upcoming and results
  const upcoming = partidos ? partidos.filter((p) => p.status === 'NS') : []
  const results = partidos ? partidos.filter((p) => p.status === 'FT') : []

  // build a list of unique dates (as ISO date) for the calendar bar based on upcoming matches
  const uniqueDates = Array.from(
    new Map(
      (upcoming || []).map((p) => {
        const d = new Date(p.date)
        const iso = d.toISOString().slice(0, 10)
        return [iso, d]
      })
    ).entries()
  ).map(([iso]) => iso)

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

  const flagClass = (team: string) => {
    const code = teamToFlag[team] || team.slice(0, 2).toLowerCase()
    return `fi fi-${code}`
  }

  const competitionOf = (p: Partido) => {
    // lightweight heuristic mapping for demo purposes
    const t = (p.home_team + ' ' + p.away_team).toLowerCase()
    if (t.includes('argentina') || t.includes('brazil')) return 'Copa América'
    if (t.includes('world') || t.includes('fifa') || t.includes('worldcup')) return 'Mundial'
    return 'Clasificatorias'
  }

  // filtered lists by date and competition
  const filteredUpcoming = upcoming.filter((p) => {
    if (selectedDate) {
      return new Date(p.date).toISOString().slice(0, 10) === selectedDate
    }
    return true
  })

  const filteredResults = results.filter((p) => {
    if (competitionFilter && competitionFilter !== 'Todos') {
      return competitionOf(p) === competitionFilter
    }
    return true
  })

  // simulate probabilities for the simulate modal
  const simulateProbs = (p: Partido) => {
    const hx = p.home_xg ?? 1
    const ax = p.away_xg ?? 1
    let home = hx / (hx + ax + 0.0001)
    let away = ax / (hx + ax + 0.0001)
    let draw = 0.15
    // normalize and reduce draw when gap is big
    const gap = Math.abs(hx - ax)
    draw = Math.max(0.05, 0.25 - gap * 0.03)
    const sum = home + away
    home = home * (1 - draw) / sum
    away = away * (1 - draw) / sum
    return {
      home: Math.round(home * 100),
      draw: Math.round(draw * 100),
      away: Math.round(away * 100),
    }
  }

  const openSimulate = (p: Partido) => {
    setSelectedMatch(p)
    setModalMode('simulate')
  }

  const openDetail = (p: Partido) => {
    setSelectedMatch(p)
    setModalMode('detail')
  }

  const closeModal = () => {
    setSelectedMatch(null)
    setModalMode(null)
  }

  return (
    <main className="min-vh-100 bg-light p-5 text-dark">
      <div className="container mt-4">
        <div className="d-flex align-items-center justify-content-between mb-3">
          <div>
            <h1 className="h3 mb-1">El Pizarrón Estadístico</h1>
            <div className="text-muted small">Tablero de partidos, resultados y predicciones</div>
          </div>
          <div className="btn-group" role="tablist" aria-label="Tabs">
            <button className={`btn btn-sm ${tab === 'upcoming' ? 'btn-primary' : 'btn-outline-secondary'}`} onClick={() => setTab('upcoming')}>Próximos Partidos</button>
            <button className={`btn btn-sm ${tab === 'results' ? 'btn-primary' : 'btn-outline-secondary'}`} onClick={() => setTab('results')}>Resultados</button>
          </div>
        </div>
        <hr className="border-top border-secondary mb-5" />

        {/* Loading / Error */}
        {(loading || partidos === null) && <div className="text-center text-muted py-4">Cargando partidos...</div>}
        {error && <div className="alert alert-danger">Error: {error}</div>}

        {/* Upcoming Tab */}
        {tab === 'upcoming' && (
          <section>
            {/* Calendar bar */}
            <div className="d-flex gap-2 overflow-auto pb-2 mb-3">
              {uniqueDates.length === 0 && <div className="text-muted">No hay días con partidos próximos</div>}
              {uniqueDates.map((iso) => {
                const d = new Date(iso)
                const label = d.toLocaleDateString(undefined, { weekday: 'short', day: '2-digit', month: 'short' })
                return (
                  <button
                    key={iso}
                    className={`btn btn-sm ${selectedDate === iso ? 'btn-primary' : 'btn-outline-secondary'}`}
                    onClick={() => setSelectedDate(selectedDate === iso ? null : iso)}
                  >
                    {label}
                  </button>
                )
              })}
            </div>

            {/* Cards grid */}
            <div className="row">
              {filteredUpcoming.map((p) => (
                <div key={p.id} className="col-12 col-md-6 mb-3">
                  <div className="card bg-white text-dark shadow-sm border-0 rounded-3 mb-3 p-4 h-100">
                    <div className="d-flex justify-content-between align-items-start">
                      <div className="small text-muted">{competitionOf(p)}</div>
                      <div className="small text-muted">{new Date(p.date).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}</div>
                    </div>

                    <div className="d-flex align-items-center justify-content-between mt-3">
                      <div className="d-flex align-items-center">
                        <span className={`${flagClass(p.home_team)} me-2`} />
                        <div>{p.home_team}</div>
                      </div>

                      <div className="text-center text-muted">vs</div>

                      <div className="d-flex align-items-center">
                        <div className="text-end me-2">{p.away_team}</div>
                        <span className={`${flagClass(p.away_team)} ms-2`} />
                      </div>
                    </div>

                    <div className="mt-3 d-flex justify-content-end">
                      <button className="btn btn-success rounded-pill" onClick={() => openSimulate(p)}>Simular Predicción</button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Results Tab */}
        {tab === 'results' && (
          <section>
            <div className="d-flex align-items-center gap-3 mb-3">
              <label className="mb-0 small text-muted">Competición:</label>
              {['Todos', 'Mundial', 'Clasificatorias', 'Copa América', 'Eurocopa', 'Champions League'].map((opt) => (
                <button
                  key={opt}
                  className={`btn btn-outline-secondary btn-sm rounded-pill me-2 ${competitionFilter === opt ? 'active' : ''}`}
                  onClick={() => setCompetitionFilter(opt)}
                >
                  {opt}
                </button>
              ))}
            </div>

            <div className="row">
              {filteredResults.map((p) => (
                <div key={p.id} className="col-12 col-md-6 mb-3">
                  <div className="card bg-white text-dark shadow-sm border-0 rounded-3 mb-3 p-4 h-100" role="button" onClick={() => openDetail(p)}>
                    <div className="d-flex align-items-center justify-content-between">
                      <div className="d-flex align-items-center">
                        <span className={`${flagClass(p.home_team)} me-2`} />
                        <div className="fw-semibold">{p.home_team}</div>
                      </div>

                      <div className="text-warning fw-bold fs-3">{formatScore(p.home_score)} - {formatScore(p.away_score)}</div>

                      <div className="d-flex align-items-center">
                        <div className="fw-semibold text-end me-2">{p.away_team}</div>
                        <span className={`${flagClass(p.away_team)} ms-2`} />
                      </div>
                    </div>

                    <div className="mt-3 text-center small text-muted">xG: {p.home_xg != null ? p.home_xg.toFixed(2) : '-'} - {p.away_xg != null ? p.away_xg.toFixed(2) : '-'}</div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Floating popup (single structure) */}
        {selectedMatch && (
          <div
            style={{
              position: 'fixed',
              top: 0,
              left: 0,
              width: '100vw',
              height: '100vh',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              zIndex: 2000,
              background: 'rgba(0,0,0,0.25)'
            }}
            onClick={() => setSelectedMatch(null)}
          >
            <div
              onClick={(e) => e.stopPropagation()}
              style={{
                maxWidth: 550,
                width: '90%',
                background: '#ffffff',
                borderRadius: 12,
                boxShadow: '0 10px 30px rgba(2,6,23,0.35)',
                padding: 20,
              }}
            >
              {/* Header with flags and title */}
              <div className="d-flex justify-content-between align-items-start mb-3">
                <div className="d-flex align-items-center">
                  <span className={`${flagClass(selectedMatch.home_team)} me-2`} />
                  <strong className="me-3">{selectedMatch.home_team}</strong>
                  <span className="text-muted">vs</span>
                  <strong className="ms-3">{selectedMatch.away_team}</strong>
                  <span className={`${flagClass(selectedMatch.away_team)} ms-2`} />
                </div>
                <button type="button" className="btn-close" aria-label="Close" onClick={() => setSelectedMatch(null)} />
              </div>

              {/* Body: xG bars or simulate probs depending on modalMode */}
              {modalMode === 'simulate' ? (
                <div>
                  <p className="small text-muted">Procesando modelo Dixon-Coles (simulado)...</p>
                  {(() => {
                    const probs = simulateProbs(selectedMatch)
                    return (
                      <div>
                        <div className="mb-2">Victoria Local: {probs.home}%</div>
                        <div className="progress mb-3"><div className="progress-bar bg-success" style={{ width: `${probs.home}%` }} /></div>

                        <div className="mb-2">Empate: {probs.draw}%</div>
                        <div className="progress mb-3"><div className="progress-bar bg-secondary" style={{ width: `${probs.draw}%` }} /></div>

                        <div className="mb-2">Victoria Visitante: {probs.away}%</div>
                        <div className="progress mb-3"><div className="progress-bar bg-danger" style={{ width: `${probs.away}%` }} /></div>
                      </div>
                    )
                  })()}
                </div>
              ) : (
                <div>
                  <div className="d-flex align-items-center gap-3 mb-3">
                    <div style={{ flex: 1 }}>
                      <div className="small text-muted">xG Local</div>
                      <div className="progress"><div className="progress-bar bg-primary" role="progressbar" style={{ width: `${(selectedMatch.home_xg ?? 0) * 20}%` }} /></div>
                      <div className="small text-muted mt-1">{selectedMatch.home_xg != null ? selectedMatch.home_xg.toFixed(2) : '-'}</div>
                    </div>

                    <div style={{ width: 80 }} className="text-center">
                      <div className="fw-bold fs-4">{formatScore(selectedMatch.home_score)} - {formatScore(selectedMatch.away_score)}</div>
                    </div>

                    <div style={{ flex: 1 }}>
                      <div className="small text-muted text-end">xG Visitante</div>
                      <div className="progress"><div className="progress-bar bg-success" role="progressbar" style={{ width: `${(selectedMatch.away_xg ?? 0) * 20}%` }} /></div>
                      <div className="small text-muted mt-1 text-end">{selectedMatch.away_xg != null ? selectedMatch.away_xg.toFixed(2) : '-'}</div>
                    </div>
                  </div>

                  <hr />

                  <table className="table table-borderless mb-0">
                    <tbody>
                      <tr>
                        <td className="small text-muted">Posesión</td>
                        <td className="text-center">54%</td>
                        <td className="text-center">46%</td>
                      </tr>
                      <tr>
                        <td className="small text-muted">Remates</td>
                        <td className="text-center">12</td>
                        <td className="text-center">8</td>
                      </tr>
                      <tr>
                        <td className="small text-muted">Faltas</td>
                        <td className="text-center">10</td>
                        <td className="text-center">14</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              )}

              {/* Footer */}
              <div className="d-flex justify-content-end mt-3">
                <button className="btn btn-secondary" onClick={() => setSelectedMatch(null)}>Cerrar</button>
              </div>
            </div>
          </div>
        )}

        {/* legacy bootstrap modal removed — using React-controlled floating card above */}
      </div>
    </main>
  )
}
