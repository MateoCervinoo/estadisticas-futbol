"use client"

import React, { useEffect, useState, useCallback } from 'react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from 'recharts'

type Tab = 'evolution' | 'xg-vs-real' | 'distribucion'
type TeamType = 'club' | 'seleccion'

export default function AnalisisPage() {
  const [tab, setTab] = useState<Tab>('evolution')
  const [teamType, setTeamType] = useState<TeamType>('club')
  const [teamQuery, setTeamQuery] = useState('')
  const [teams, setTeams] = useState<{ id: number; nombre: string; codigo_bandera: string | null }[]>([])
  const [selectedTeam, setSelectedTeam] = useState<{ id: number; nombre: string } | null>(null)
  const [evolution, setEvolution] = useState<any[]>([])
  const [distribucion, setDistribucion] = useState<any[]>([])
  const [xgData, setXgData] = useState<any[]>([])
  const [evolLoading, setEvolLoading] = useState(false)
  const [xgLoading, setXgLoading] = useState(false)
  const [distLoading, setDistLoading] = useState(false)

  const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  // Debounced team search
  useEffect(() => {
    if (teamQuery.trim().length < 2) {
      setTeams([])
      return
    }
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`${BASE_URL}/api/equipos/search?q=${encodeURIComponent(teamQuery)}&tipo=${teamType}`)
        if (res.ok) setTeams(await res.json())
      } catch {}
    }, 300)
    return () => clearTimeout(timer)
  }, [teamQuery, teamType, BASE_URL])

  // Fetch evolution when a team is selected
  useEffect(() => {
    if (!selectedTeam) return
    setEvolLoading(true)
    fetch(`${BASE_URL}/api/equipos/${selectedTeam.id}/evolution`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data) setEvolution(data.evolution || [])
        setEvolLoading(false)
      })
      .catch(() => setEvolLoading(false))
  }, [selectedTeam, BASE_URL])

  // Fetch distribution when a team is selected
  useEffect(() => {
    if (!selectedTeam) return
    setDistLoading(true)
    fetch(`${BASE_URL}/api/equipos/${selectedTeam.id}/distribucion`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data) setDistribucion(data.distribucion || [])
        setDistLoading(false)
      })
      .catch(() => setDistLoading(false))
  }, [selectedTeam, BASE_URL])

  // Fetch xG vs real data
  useEffect(() => {
    if (tab !== 'xg-vs-real') return
    setXgLoading(true)
    fetch(`${BASE_URL}/api/analytics/xg-vs-real?tipo=${teamType}`)
      .then((r) => r.ok ? r.json() : null)
      .then((data) => {
        if (data) setXgData(data)
        setXgLoading(false)
      })
      .catch(() => setXgLoading(false))
  }, [tab, teamType, BASE_URL])

  const selectTeam = useCallback((t: { id: number; nombre: string }) => {
    setSelectedTeam(t)
    setTeamQuery('')
    setTeams([])
  }, [])

  const changeTeamType = useCallback((type: TeamType) => {
    setTeamType(type)
    setSelectedTeam(null)
    setTeamQuery('')
    setTeams([])
    setEvolution([])
    setDistribucion([])
    setXgData([])
  }, [])

  const downloadCSV = useCallback(() => {
    if (xgData.length === 0) return
    const headers = ['Equipo', 'PJ', 'Goles', 'xG', 'xGA', 'Dif G-xG', 'Dif xG-xGA', 'Goles p90', 'xG p90', 'xGA p90']
    const rows = xgData.map((r: any) => [
      r.nombre, r.pj, r.goles, r.xg, r.xga, r.diferencia, r.xg_diff, r.goles_p90, r.xg_p90, r.xga_p90,
    ])
    const csv = [headers.join(','), ...rows.map((r: Array<string | number>) => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'xg_vs_real.csv'; a.click()
    URL.revokeObjectURL(url)
  }, [xgData])

  return (
    <main className="min-vh-100 bg-light p-4 text-dark">
      <div className="container mt-3">
        <h4 className="mb-3">
          Análisis Avanzado
          <small className="text-muted ms-2" style={{ fontSize: '0.7rem' }}>Evolución, xG vs real y distribución Poisson</small>
        </h4>

        {/* Team selector */}
        <div className="card shadow-sm border-0 rounded-3 mb-4">
          <div className="card-body">
            <div className="btn-group btn-group-sm mb-3" role="group" aria-label="Tipo de equipo">
              <button
                type="button"
                className={`btn ${teamType === 'club' ? 'btn-primary' : 'btn-outline-primary'}`}
                onClick={() => changeTeamType('club')}
              >
                Clubes
              </button>
              <button
                type="button"
                className={`btn ${teamType === 'seleccion' ? 'btn-primary' : 'btn-outline-primary'}`}
                onClick={() => changeTeamType('seleccion')}
              >
                Selecciones
              </button>
            </div>
            {selectedTeam ? (
              <div className="d-flex align-items-center justify-content-between">
                <span className="fw-semibold">{selectedTeam.nombre}</span>
                <button className="btn btn-sm btn-outline-secondary" onClick={() => setSelectedTeam(null)}>Cambiar equipo</button>
              </div>
            ) : (
              <div className="position-relative">
                <label className="form-label small fw-semibold">Buscar equipo</label>
                <input
                  className="form-control"
                  placeholder="Escribí al menos 2 caracteres..."
                  value={teamQuery}
                  onChange={(e) => setTeamQuery(e.target.value)}
                />
                {teams.length > 0 && (
                  <ul className="list-group position-absolute w-100 shadow" style={{ zIndex: 1050, maxHeight: 250, overflowY: 'auto' }}>
                    {teams.map((t) => (
                      <li
                        key={t.id}
                        className="list-group-item list-group-item-action py-2"
                        onClick={() => selectTeam(t)}
                        role="button"
                      >
                        {t.codigo_bandera && <span className={`fi fi-${t.codigo_bandera} me-2`} />}
                        {t.nombre}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Tabs */}
        <ul className="nav nav-tabs mb-3">
          <li className="nav-item">
            <button className={`nav-link ${tab === 'evolution' ? 'active fw-semibold' : ''}`} onClick={() => setTab('evolution')}>
              Evolución Ataque/Defensa
            </button>
          </li>
          <li className="nav-item">
            <button className={`nav-link ${tab === 'xg-vs-real' ? 'active fw-semibold' : ''}`} onClick={() => setTab('xg-vs-real')}>
              xG vs Goles Reales
            </button>
          </li>
          <li className="nav-item">
            <button className={`nav-link ${tab === 'distribucion' ? 'active fw-semibold' : ''}`} onClick={() => setTab('distribucion')}>
              Distribución Poisson
            </button>
          </li>
        </ul>

        {/* Tab: Evolution */}
        {tab === 'evolution' && (
          <div>
            {!selectedTeam && <div className="text-muted text-center py-5">Seleccioná un equipo para ver su evolución</div>}
            {evolLoading && <div className="text-muted text-center py-5">Cargando evolución...</div>}
            {!evolLoading && selectedTeam && evolution.length === 0 && (
              <div className="text-muted text-center py-5">No hay datos de evolución para este equipo</div>
            )}
            {!evolLoading && evolution.length > 0 && (
              <div className="card shadow-sm border-0 rounded-3 p-3">
                <p className="small text-muted mb-3">
                  Media móvil de goles a favor y en contra (ventana de 5 partidos)
                </p>
                <ResponsiveContainer width="100%" height={350}>
                  <LineChart data={evolution}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="match_index" label={{ value: 'Partido #', position: 'insideBottomRight', offset: -5 }} />
                    <YAxis label={{ value: 'Goles', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="rolling_gf_avg" stroke="#28a745" strokeWidth={2} dot={false} name="Goles a favor (media 5)" />
                    <Line type="monotone" dataKey="rolling_gc_avg" stroke="#dc3545" strokeWidth={2} dot={false} name="Goles en contra (media 5)" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}

        {/* Tab: xG vs Real */}
        {tab === 'xg-vs-real' && (
          <div>
            {xgLoading && <div className="text-muted text-center py-5">Cargando datos xG...</div>}
            {!xgLoading && xgData.length === 0 && (
              <div className="text-muted text-center py-5">No hay datos xG disponibles</div>
            )}
            {!xgLoading && xgData.length > 0 && (
              <div>
                <div className="d-flex justify-content-end mb-2">
                  <button className="btn btn-sm btn-outline-secondary" onClick={downloadCSV}>
                    Exportar CSV
                  </button>
                </div>
                <div className="card shadow-sm border-0 rounded-3 p-3">
                  <p className="small text-muted mb-3">Goles reales, xG y xGA por equipo (todos los torneos)</p>
                  <ResponsiveContainer width="100%" height={500}>
                    <BarChart data={xgData.slice(0, 30)} layout="vertical" margin={{ left: 120 }}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis type="number" />
                      <YAxis type="category" dataKey="nombre" width={110} tick={{ fontSize: 11 }} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="goles_p90" fill="#28a745" name="Goles p90" />
                      <Bar dataKey="xg_p90" fill="#ffc107" name="xG p90" />
                      <Bar dataKey="xga_p90" fill="#dc3545" name="xGA p90" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-3">
                  <div className="table-responsive">
                    <table className="table table-sm table-striped">
                      <thead>
                        <tr>
                          <th>Equipo</th>
                          <th className="text-end">PJ</th>
                          <th className="text-end">Goles</th>
                          <th className="text-end">xG</th>
                          <th className="text-end">xGA</th>
                          <th className="text-end">G-xG</th>
                          <th className="text-end">xG-xGA</th>
                          <th className="text-end">G/p90</th>
                          <th className="text-end">xG/p90</th>
                          <th className="text-end">xGA/p90</th>
                        </tr>
                      </thead>
                      <tbody>
                        {xgData.map((r: any) => (
                          <tr key={r.equipo_id}>
                            <td>{r.codigo_bandera && <span className={`fi fi-${r.codigo_bandera} me-1`} />}{r.nombre}</td>
                            <td className="text-end">{r.pj}</td>
                            <td className="text-end">{r.goles}</td>
                            <td className="text-end">{r.xg}</td>
                            <td className="text-end">{r.xga}</td>
                            <td className={`text-end fw-semibold ${r.diferencia > 0 ? 'text-success' : r.diferencia < 0 ? 'text-danger' : ''}`}>
                              {r.diferencia > 0 ? '+' : ''}{r.diferencia}
                            </td>
                            <td className={`text-end fw-semibold ${r.xg_diff > 0 ? 'text-success' : r.xg_diff < 0 ? 'text-danger' : ''}`}>
                              {r.xg_diff > 0 ? '+' : ''}{r.xg_diff}
                            </td>
                            <td className="text-end">{r.goles_p90}</td>
                            <td className="text-end">{r.xg_p90}</td>
                            <td className="text-end">{r.xga_p90}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab: Distribution */}
        {tab === 'distribucion' && (
          <div>
            {!selectedTeam && <div className="text-muted text-center py-5">Seleccioná un equipo para ver su distribución Poisson</div>}
            {distLoading && <div className="text-muted text-center py-5">Cargando distribución...</div>}
            {!distLoading && selectedTeam && distribucion.length === 0 && (
              <div className="text-muted text-center py-5">No hay datos de distribución para este equipo</div>
            )}
            {!distLoading && distribucion.length > 0 && (
              <div className="card shadow-sm border-0 rounded-3 p-3">
                <p className="small text-muted mb-3">
                  Frecuencia real de goles anotados vs. distribución Poisson esperada
                </p>
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart data={distribucion}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="goles" label={{ value: 'Goles anotados', position: 'insideBottomRight', offset: -5 }} />
                    <YAxis label={{ value: '%', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="actual_pct" fill="#28a745" name="Real %" />
                    <Bar dataKey="poisson_pct" fill="#ffc107" name="Poisson %" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  )
}
