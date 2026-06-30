"use client"

import React, { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  getTablaPosiciones, getBracket, getPartidos, getPartidoEstadisticas, getTorneoTemporadas,
  TablaRow, TablaGrupo, BracketRound, Partido,
} from '../../../src/services/api'

type Tab = 'calendario' | 'posiciones' | 'eliminatorias' | 'estadisticas'

const TOURNAMENT_LABELS: Record<string, string> = {
  Mundial: 'Mundial', Clasificatorias: 'Clasificatorias', Amistoso: 'Amistoso',
  'Copa América': 'Copa América', Eurocopa: 'Eurocopa',
  'Nations League': 'Nations League', Confederaciones: 'Copa Confederaciones',
  'Copa Africana de Naciones': 'Copa Africana', 'Copa Asiática': 'Copa Asiática',
  'Copa Oro': 'Copa Oro', 'Juegos Olímpicos': 'Juegos Olímpicos',
  FIFA_WORLD_CUP: 'Mundial', WORLD_CUP: 'Mundial',
}

const STAGE_LABELS: Record<string, string> = {
  GROUP_STAGE: 'Fase de Grupos', LAST_32: 'Dieciseisavos de Final', ROUND_OF_32: 'Dieciseisavos de Final',
  LAST_16: 'Octavos de Final', ROUND_OF_16: 'Octavos de Final',
  QUARTER_FINALS: 'Cuartos de Final', SEMI_FINALS: 'Semifinales',
  THIRD_PLACE: 'Tercer Puesto', FINAL: 'Final',
}

const StatRow = ({ label, home, away, fmt = 'int' }: { label: string; home: number; away: number; fmt?: 'int' | 'float' | 'pct' }) => {
  const fmtVal = (v: number) => {
    if (fmt === 'pct') return `${Math.round(v)}%`
    if (fmt === 'float') return v.toFixed(2)
    return String(Math.round(v))
  }
  const total = home + away
  const homePct = total > 0 ? (home / total) * 100 : 50
  const homeBar = homePct < 10 ? 10 : homePct > 90 ? 90 : homePct
  const awayBar = 100 - homeBar
  return (
    <div>
      <div className="d-flex justify-content-between small mb-1">
        <span className="fw-semibold">{fmtVal(home)}</span>
        <span className="text-muted">{label}</span>
        <span className="fw-semibold">{fmtVal(away)}</span>
      </div>
      <div className="progress" style={{ height: 6 }}>
        <div className="progress-bar bg-success" style={{ width: `${homeBar}%` }} />
        <div className="progress-bar bg-danger" style={{ width: `${awayBar}%` }} />
      </div>
    </div>
  )
}

export default function TorneoDetailPage() {
  const params = useParams()
  const torneoId = Number(params.id)
  const [activeTab, setActiveTab] = useState<Tab>('calendario')
  const [tabla, setTabla] = useState<TablaRow[] | null>(null)
  const [tablaGrupos, setTablaGrupos] = useState<TablaGrupo[] | null>(null)
  const [bracket, setBracketData] = useState<BracketRound[] | null>(null)
  const [partidos, setPartidos] = useState<Partido[] | null>(null)
  const [torName, setTorName] = useState('')
  const [torTipo, setTorTipo] = useState('')
  const [temporadas, setTemporadas] = useState<string[]>([])
  const [selectedSeason, setSelectedSeason] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [sortCol, setSortCol] = useState<string>('pts')
  const [sortAsc, setSortAsc] = useState(false)
  // detail modal
  const [selectedMatch, setSelectedMatch] = useState<Partido | null>(null)
  const [currentStats, setCurrentStats] = useState<any>(null)
  const [statsLoading, setStatsLoading] = useState(false)

  useEffect(() => {
    getTorneoTemporadas(torneoId).then((values) => {
      setTemporadas(values)
      setSelectedSeason((current) => current || values[0] || '')
    })
  }, [torneoId])

  useEffect(() => {
    if (!selectedSeason) return
    setLoading(true)
    const seasonFilters = /^\d{4}$/.test(selectedSeason)
      ? { year: Number(selectedSeason), grouped: true }
      : { season: selectedSeason, grouped: true }
    const matchFilters = /^\d{4}$/.test(selectedSeason)
      ? { torneo_id: torneoId, year: Number(selectedSeason) }
      : { torneo_id: torneoId, season: selectedSeason }
    Promise.all([
      getTablaPosiciones(torneoId, seasonFilters),
      getBracket(torneoId, seasonFilters),
      getPartidos(matchFilters),
    ]).then(([t, b, ps]) => {
      if (t) {
        setTabla(t.tabla)
        setTablaGrupos(t.grupos ?? null)
        setTorName(t.torneo)
        setTorTipo(t.tipo)
      }
      if (b) setBracketData(b.bracket)
      if (ps) setPartidos(ps)
      setLoading(false)
    })
  }, [torneoId, selectedSeason])

  const formatDate = (iso: string) => {
    try {
      return new Date(iso.endsWith('Z') ? iso : `${iso}Z`).toLocaleString('es-AR', {
        timeZone: 'America/Argentina/Buenos_Aires',
        weekday: 'short', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
      })
    } catch { return iso }
  }

  const isPlayed = (p: Partido) => {
    if (['NS', 'TIMED', 'SCHEDULED', 'IN_PLAY', 'PAUSED'].includes(p.status)) return false
    return (p.home_score !== null && p.home_score !== undefined && p.away_score !== null && p.away_score !== undefined)
      || ['FT', 'AET', 'PEN'].includes(p.status)
  }

  const sortedTabla = useMemo(() => {
    if (!tabla) return []
    const col = sortCol as keyof TablaRow
    return [...tabla].sort((a, b) => {
      const av = Number(a[col] ?? 0)
      const bv = Number(b[col] ?? 0)
      return sortAsc ? av - bv : bv - av
    })
  }, [tabla, sortCol, sortAsc])

  const toggleSort = (col: string) => {
    if (sortCol === col) setSortAsc(!sortAsc)
    else { setSortCol(col); setSortAsc(false) }
  }

  const sortIcon = (col: string) => {
    if (sortCol !== col) return ''
    return sortAsc ? ' ▲' : ' ▼'
  }

  const renderTabla = (rows: TablaRow[]) => (
    <div className="table-responsive">
      <table className="table table-hover table-sm align-middle">
        <thead className="table-light">
          <tr>
            <th>#</th>
            <th>Equipo</th>
            <th className="text-center" style={{cursor:'pointer'}} onClick={() => toggleSort('pj')}>PJ{sortIcon('pj')}</th>
            <th className="text-center" style={{cursor:'pointer'}} onClick={() => toggleSort('pg')}>PG{sortIcon('pg')}</th>
            <th className="text-center" style={{cursor:'pointer'}} onClick={() => toggleSort('pe')}>PE{sortIcon('pe')}</th>
            <th className="text-center" style={{cursor:'pointer'}} onClick={() => toggleSort('pp')}>PP{sortIcon('pp')}</th>
            <th className="text-center" style={{cursor:'pointer'}} onClick={() => toggleSort('gf')}>GF{sortIcon('gf')}</th>
            <th className="text-center" style={{cursor:'pointer'}} onClick={() => toggleSort('gc')}>GC{sortIcon('gc')}</th>
            <th className="text-center" style={{cursor:'pointer'}} onClick={() => toggleSort('gd')}>GD{sortIcon('gd')}</th>
            <th className="text-center" style={{cursor:'pointer'}} onClick={() => toggleSort('xg_diff')}>xG Diff{sortIcon('xg_diff')}</th>
            <th className="text-center fw-bold" style={{cursor:'pointer'}} onClick={() => toggleSort('pts')}>Pts{sortIcon('pts')}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => {
            const xgColor = r.xg_diff > 0 ? 'text-success' : r.xg_diff < 0 ? 'text-danger' : ''
            return (
              <tr key={r.equipo_id}>
                <td className="text-muted">{i + 1}</td>
                <td>
                  <Link href={`/equipos/${r.equipo_id}`} className="text-decoration-none text-dark d-flex align-items-center gap-2">
                    {r.codigo_bandera && <span className={`fi fi-${r.codigo_bandera}`} />}
                    {r.equipo}
                  </Link>
                </td>
                <td className="text-center">{r.pj}</td>
                <td className="text-center">{r.pg}</td>
                <td className="text-center">{r.pe}</td>
                <td className="text-center">{r.pp}</td>
                <td className="text-center">{r.gf}</td>
                <td className="text-center">{r.gc}</td>
                <td className="text-center">{r.gd > 0 ? `+${r.gd}` : r.gd}</td>
                <td className={`text-center ${xgColor}`}>{r.xg_diff > 0 ? `+${r.xg_diff}` : r.xg_diff}</td>
                <td className="text-center fw-bold">{r.pts}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )

  const formaBadge = (resultado: string) => {
    const map: Record<string, string> = { H: 'bg-success', A: 'bg-danger', D: 'bg-warning text-dark' }
    return <span className={`badge ${map[resultado] || 'bg-secondary'} me-1`}>{resultado}</span>
  }

  const flagClass = (team: string, code?: string | null) => {
    const c = (code || team.slice(0, 2)).toLowerCase()
    return `fi fi-${c}`
  }

  const openDetail = (p: Partido) => {
    setSelectedMatch(p)
    setCurrentStats(null)
    setStatsLoading(true)
    getPartidoEstadisticas(p.id).then(stats => {
      setCurrentStats(stats)
      setStatsLoading(false)
    })
  }

  const closeModal = () => { setSelectedMatch(null); setCurrentStats(null) }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'calendario', label: 'Calendario' },
    { key: 'posiciones', label: 'Posiciones' },
    { key: 'eliminatorias', label: 'Eliminatorias' },
    { key: 'estadisticas', label: 'Estadísticas' },
  ]

  return (
    <main className="container py-4">
      <div className="d-flex align-items-center gap-3 mb-4">
        <Link href="/torneos" className="btn btn-outline-secondary btn-sm">&larr; Torneos</Link>
        <h3 className="mb-0">{torName || 'Torneo'}</h3>
        <span className="badge bg-secondary">{torTipo}</span>
        {temporadas.length > 0 && (
          <select
            className="form-select form-select-sm ms-auto"
            style={{ maxWidth: 160 }}
            value={selectedSeason}
            onChange={(e) => setSelectedSeason(e.target.value)}
            aria-label="Temporada"
          >
            {temporadas.map((season) => (
              <option key={season} value={season}>{season}</option>
            ))}
          </select>
        )}
      </div>

      <ul className="nav nav-tabs mb-4">
        {tabs.map(t => (
          <li key={t.key} className="nav-item">
            <button className={`nav-link ${activeTab === t.key ? 'active fw-semibold' : ''}`}
              onClick={() => setActiveTab(t.key)}>{t.label}</button>
          </li>
        ))}
      </ul>

      {loading && <div className="text-muted">Cargando...</div>}

      {/* ──────── TAB: CALENDARIO ──────── */}
      {!loading && activeTab === 'calendario' && (
        <div>
          {(!partidos || partidos.length === 0) && (
            <div className="text-muted text-center py-5">No hay partidos para este torneo.</div>
          )}
          <div className="row">
            {partidos?.map(p => (
              <div key={p.id} className="col-12 col-md-6 mb-3">
                <div className="card bg-white shadow-sm border-0 rounded-3 p-4">
                  <div className="d-flex justify-content-between align-items-start gap-3">
                    <div className="small text-muted">
                      {STAGE_LABELS[p.stage?.trim() || ''] || p.stage || ''}
                      {p.group ? ` · ${p.group.replace('GROUP_', 'Grupo ')}` : ''}
                    </div>
                    <div className="small text-muted text-end">{formatDate(p.date)}</div>
                  </div>
                  <div className="d-flex align-items-center justify-content-between gap-3 mt-3">
                    <div className="d-flex align-items-center flex-fill">
                      <span className={`${flagClass(p.home_team, p.home_codigo_bandera)} me-2`} />
                      <div className="fw-semibold">{p.home_team}</div>
                    </div>
                    <div className="text-center">
                      {isPlayed(p) ? (
                        <div className="fs-4 fw-bold">{p.home_score} - {p.away_score}</div>
                      ) : <div className="text-muted">vs</div>}
                    </div>
                    <div className="d-flex align-items-center justify-content-end flex-fill">
                      <div className="fw-semibold text-end me-2">{p.away_team}</div>
                      <span className={`${flagClass(p.away_team, p.away_codigo_bandera)}`} />
                    </div>
                  </div>
                  <div className="mt-3 d-flex justify-content-end">
                    {isPlayed(p) ? (
                      <button className="btn btn-outline-secondary rounded-pill btn-sm" onClick={() => openDetail(p)}>Ver detalle</button>
                    ) : (
                      <span className="text-muted small">Próximamente</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ──────── TAB: POSICIONES ──────── */}
      {!loading && activeTab === 'posiciones' && (
        <div>
          {tablaGrupos && tablaGrupos.length > 0 ? (
            <div className="vstack gap-4">
              {tablaGrupos.map((group) => (
                <section key={group.grupo}>
                  <h5 className="mb-3">{group.grupo.replace('GROUP_', 'Grupo ')}</h5>
                  {renderTabla(group.tabla)}
                </section>
              ))}
            </div>
          ) : (
            <>
              {(!tabla || tabla.length === 0) && <div className="text-muted text-center py-5">No hay datos de posiciones.</div>}
              {tabla && tabla.length > 0 && renderTabla(sortedTabla)}
            </>
          )}
        </div>
      )}

      {/* ──────── TAB: ELIMINATORIAS ──────── */}
      {!loading && activeTab === 'eliminatorias' && (
        <div>
          {(!bracket || bracket.length === 0) && <div className="text-muted text-center py-5">No hay eliminatorias para este torneo.</div>}
          {bracket && bracket.length > 0 && (
            <div className="vstack gap-4">
              {bracket.filter(r => r.stage !== 'GROUP_STAGE').map(ronda => (
                <div key={ronda.stage}>
                  <h5 className="mb-3">{ronda.label}</h5>
                  <div className="row">
                    {ronda.matches.map(m => (
                      <div key={m.partido_id} className="col-12 col-md-6 col-lg-4 mb-2">
                        <div className="card bg-white shadow-sm border-0 rounded-3 p-3">
                          <div className="d-flex align-items-center justify-content-between gap-2">
                            <div className="fw-semibold small flex-fill">{m.home_team}</div>
                            <div className="text-center">
                              {m.home_score !== null ? (
                                <span className="fw-bold">{m.home_score} - {m.away_score}</span>
                              ) : <span className="text-muted small">vs</span>}
                            </div>
                            <div className="fw-semibold small flex-fill text-end">{m.away_team}</div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ──────── TAB: ESTADÍSTICAS ──────── */}
      {!loading && activeTab === 'estadisticas' && (
        <div>
          {tabla && tabla.length > 0 && (
            <div className="row g-4">
              <div className="col-12 col-md-6">
                <div className="card bg-white shadow-sm border-0 rounded-3 p-4">
                  <h6 className="fw-semibold mb-3">Ataque</h6>
                  <div className="vstack gap-2 small">
                    {[...tabla].sort((a, b) => b.gf - a.gf).slice(0, 5).map(r => (
                      <div key={r.equipo_id} className="d-flex justify-content-between">
                        <span>{r.equipo}</span><span className="fw-semibold">{r.gf} goles</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="col-12 col-md-6">
                <div className="card bg-white shadow-sm border-0 rounded-3 p-4">
                  <h6 className="fw-semibold mb-3">Defensa</h6>
                  <div className="vstack gap-2 small">
                    {[...tabla].sort((a, b) => a.gc - b.gc).slice(0, 5).map(r => (
                      <div key={r.equipo_id} className="d-flex justify-content-between">
                        <span>{r.equipo}</span><span className="fw-semibold">{r.gc} recibidos</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="col-12 col-md-6">
                <div className="card bg-white shadow-sm border-0 rounded-3 p-4">
                  <h6 className="fw-semibold mb-3">xG Favor</h6>
                  <div className="vstack gap-2 small">
                    {[...tabla].sort((a, b) => b.xg_favor - a.xg_favor).slice(0, 5).map(r => (
                      <div key={r.equipo_id} className="d-flex justify-content-between">
                        <span>{r.equipo}</span><span className="fw-semibold">{r.xg_favor}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
              <div className="col-12 col-md-6">
                <div className="card bg-white shadow-sm border-0 rounded-3 p-4">
                  <h6 className="fw-semibold mb-3">Promedio de Goles</h6>
                  {(() => {
                    const totalPJ = tabla.reduce((s, r) => s + r.pj, 0)
                    const totalGF = tabla.reduce((s, r) => s + r.gf, 0)
                    const avg = totalPJ > 0 ? (totalGF / totalPJ) : 0
                    return <div className="text-center"><span className="fs-3 fw-bold">{avg.toFixed(2)}</span><div className="small text-muted">goles/partido</div></div>
                  })()}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ──── Detail Modal ──── */}
      {selectedMatch && (
        <>
          <div className="modal fade show d-block" tabIndex={-1} onClick={closeModal}>
            <div className="modal-dialog modal-lg modal-dialog-centered" onClick={e => e.stopPropagation()}>
              <div className="modal-content bg-white text-dark border-0 shadow">
                <div className="modal-header bg-light">
                  <h5 className="modal-title">{selectedMatch.home_team} vs {selectedMatch.away_team}</h5>
                  <button className="btn-close" onClick={closeModal} />
                </div>
                <div className="modal-body">
                  <div className="d-flex align-items-center justify-content-between py-3">
                    <div className="fw-semibold">{selectedMatch.home_team}</div>
                    <div className="fw-bold fs-4">{selectedMatch.home_score} - {selectedMatch.away_score}</div>
                    <div className="fw-semibold">{selectedMatch.away_team}</div>
                  </div>
                  {statsLoading && <div className="text-muted small text-center">Cargando estadísticas...</div>}
                  {!statsLoading && currentStats && (
                    <div className="vstack gap-2">
                      {currentStats.xg_local != null && <StatRow label="xG" home={currentStats.xg_local} away={currentStats.xg_visitante} fmt="float" />}
                      {currentStats.remates_local != null && <StatRow label="Remates" home={currentStats.remates_local} away={currentStats.remates_visitante} />}
                      {currentStats.posesion_local != null && <StatRow label="Posesión" home={currentStats.posesion_local} away={currentStats.posesion_visitante} fmt="pct" />}
                    </div>
                  )}
                  {!statsLoading && !currentStats && <div className="text-muted small text-center py-3">Estadísticas no disponibles.</div>}
                </div>
                <div className="modal-footer bg-light">
                  <button className="btn btn-secondary" onClick={closeModal}>Cerrar</button>
                </div>
              </div>
            </div>
          </div>
          <div className="modal-backdrop fade show" />
        </>
      )}
    </main>
  )
}
