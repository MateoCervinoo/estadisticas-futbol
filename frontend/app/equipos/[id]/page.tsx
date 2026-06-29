"use client"

import React, { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  getEquipoPerfil, getComparacion,
  EquipoPerfil, Comparacion,
} from '../../../src/services/api'

export default function EquipoPage() {
  const params = useParams()
  const router = useRouter()
  const equipoId = Number(params.id)
  const [perfil, setPerfil] = useState<EquipoPerfil | null>(null)
  const [loading, setLoading] = useState(true)
  const [compareId, setCompareId] = useState<string>('')
  const [comparacion, setComparacion] = useState<Comparacion | null>(null)
  const [compLoading, setCompLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    getEquipoPerfil(equipoId).then(data => {
      setPerfil(data)
      setLoading(false)
    })
  }, [equipoId])

  const formaBadge = (r: string) => {
    const map: Record<string, string> = { H: 'bg-success', A: 'bg-danger', D: 'bg-warning text-dark' }
    return <span className={`badge ${map[r] || 'bg-secondary'} me-1`}>{r}</span>
  }

  const handleCompare = async () => {
    const id2 = Number(compareId)
    if (!id2 || id2 === equipoId) return
    setCompLoading(true)
    const data = await getComparacion(equipoId, id2)
    setComparacion(data)
    setCompLoading(false)
  }

  if (loading) return <main className="container py-4"><div className="text-muted">Cargando perfil...</div></main>
  if (!perfil) return <main className="container py-4"><div className="text-muted">Equipo no encontrado.</div></main>

  const radarData = [
    { label: 'Goles', v1: perfil.stats.gf, v2: comparacion?.equipo2.stats.gf ?? 0 },
    { label: 'Ataque', v1: perfil.stats.gf / Math.max(perfil.stats.pj, 1), v2: comparacion ? (comparacion.equipo2.stats.gf / Math.max(comparacion.equipo2.stats.pj, 1)) : 0 },
    { label: 'Defensa', v1: -perfil.stats.gc / Math.max(perfil.stats.pj, 1), v2: comparacion ? (-comparacion.equipo2.stats.gc / Math.max(comparacion.equipo2.stats.pj, 1)) : 0 },
    { label: 'Puntos', v1: perfil.stats.pts, v2: comparacion?.equipo2.stats.pts ?? 0 },
  ]
  const maxRadar = Math.max(...radarData.map(d => Math.max(Math.abs(d.v1), Math.abs(d.v2))), 1)

  return (
    <main className="container py-4">
      <div className="d-flex align-items-center gap-3 mb-4">
        <Link href="/" className="btn btn-outline-secondary btn-sm">&larr; Volver</Link>
        <h3 className="mb-0">
          {perfil.codigo_bandera && <span className={`fi fi-${perfil.codigo_bandera} me-2`} />}
          {perfil.nombre}
        </h3>
      </div>

      {/* Stats card */}
      <div className="row g-3 mb-4">
        <div className="col-12 col-md-8">
          <div className="card bg-white shadow-sm border-0 rounded-3 p-4">
            <h6 className="fw-semibold mb-3">Estadísticas totales</h6>
            <div className="row text-center g-3">
              {[
                { label: 'PJ', value: perfil.stats.pj },
                { label: 'PG', value: perfil.stats.pg },
                { label: 'PE', value: perfil.stats.pe },
                { label: 'PP', value: perfil.stats.pp },
                { label: 'GF', value: perfil.stats.gf },
                { label: 'GC', value: perfil.stats.gc },
                { label: 'GD', value: perfil.stats.gd > 0 ? `+${perfil.stats.gd}` : perfil.stats.gd },
                { label: 'Pts', value: perfil.stats.pts },
              ].map(s => (
                <div key={s.label} className="col-3 col-md-3">
                  <div className="fw-bold fs-5">{s.value}</div>
                  <div className="small text-muted">{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Forma */}
        <div className="col-12 col-md-4">
          <div className="card bg-white shadow-sm border-0 rounded-3 p-4 h-100">
            <h6 className="fw-semibold mb-3">Últimos 5</h6>
            {perfil.forma.length === 0 && <div className="text-muted small">Sin partidos</div>}
            <div className="vstack gap-2">
              {perfil.forma.map(f => (
                <div key={f.partido_id} className="d-flex justify-content-between align-items-center small">
                  <div>{formaBadge(f.resultado)}</div>
                  <div>{f.goles_favor}-{f.goles_contra}</div>
                  <div className="text-muted text-truncate ms-2" style={{ maxWidth: 120 }}>{f.rival}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Próximos partidos */}
      {perfil.proximos.length > 0 && (
        <div className="card bg-white shadow-sm border-0 rounded-3 p-4 mb-4">
          <h6 className="fw-semibold mb-3">Próximos partidos</h6>
          <div className="vstack gap-2">
            {perfil.proximos.map(p => (
              <div key={p.partido_id} className="d-flex justify-content-between align-items-center small">
                <span>{p.local ? 'Local' : 'Visitante'} vs <strong>{p.rival}</strong></span>
                <span className="text-muted">{p.fecha ? new Date(p.fecha).toLocaleDateString('es-AR') : '-'}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Comparador */}
      <div className="card bg-white shadow-sm border-0 rounded-3 p-4">
        <h6 className="fw-semibold mb-3">Comparar con otro equipo</h6>
        <div className="d-flex gap-2 mb-3">
          <input className="form-control form-control-sm" placeholder="ID del equipo"
            value={compareId} onChange={e => setCompareId(e.target.value)} />
          <button className="btn btn-primary btn-sm" onClick={handleCompare} disabled={compLoading}>
            {compLoading ? '...' : 'Comparar'}
          </button>
        </div>

        {comparacion && (
          <div>
            <div className="table-responsive">
              <table className="table table-sm table-bordered align-middle">
                <thead className="table-light">
                  <tr>
                    <th>Métrica</th>
                    <th className="text-center">{comparacion.equipo1.nombre}</th>
                    <th className="text-center">{comparacion.equipo2.nombre}</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { label: 'Partidos', v1: comparacion.equipo1.stats.pj, v2: comparacion.equipo2.stats.pj },
                    { label: 'Victorias', v1: comparacion.equipo1.stats.pg, v2: comparacion.equipo2.stats.pg },
                    { label: 'Empates', v1: comparacion.equipo1.stats.pe, v2: comparacion.equipo2.stats.pe },
                    { label: 'Derrotas', v1: comparacion.equipo1.stats.pp, v2: comparacion.equipo2.stats.pp },
                    { label: 'Goles Favor', v1: comparacion.equipo1.stats.gf, v2: comparacion.equipo2.stats.gf },
                    { label: 'Goles Contra', v1: comparacion.equipo1.stats.gc, v2: comparacion.equipo2.stats.gc },
                    { label: 'Diferencia', v1: comparacion.equipo1.stats.gd, v2: comparacion.equipo2.stats.gd },
                    { label: 'xG Favor', v1: comparacion.equipo1.stats.xg_favor, v2: comparacion.equipo2.stats.xg_favor },
                    { label: 'xG Contra', v1: comparacion.equipo1.stats.xg_contra, v2: comparacion.equipo2.stats.xg_contra },
                    { label: 'Puntos', v1: comparacion.equipo1.stats.pts, v2: comparacion.equipo2.stats.pts },
                  ].map(row => {
                    const better = row.v1 > row.v2 ? 'text-success fw-bold' : row.v1 < row.v2 ? 'text-danger' : ''
                    return (
                      <tr key={row.label}>
                        <td>{row.label}</td>
                        <td className={`text-center ${better}`}>{row.v1}</td>
                        <td className={`text-center ${row.v1 < row.v2 ? 'text-success fw-bold' : row.v1 > row.v2 ? 'text-danger' : ''}`}>{row.v2}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <h6 className="fw-semibold mt-4 mb-2">Radar Chart (valores normalizados)</h6>
            <div className="d-flex justify-content-center">
              <svg viewBox="0 0 300 300" style={{ width: 300, height: 300 }}>
                {(() => {
                  const cx = 150, cy = 150, r = 120
                  const angles = radarData.map((_, i) => (2 * Math.PI * i) / radarData.length - Math.PI / 2)
                  const levels = [0.25, 0.5, 0.75, 1.0]
                  const points = (vals: number[]) => vals.map((v, i) => {
                    const ratio = v / maxRadar
                    const x = cx + r * ratio * Math.cos(angles[i])
                    const y = cy + r * ratio * Math.sin(angles[i])
                    return `${x},${y}`
                  }).join(' ')

                  const gridLines = levels.map(l => {
                    const pts = radarData.map((_, i) => {
                      const x = cx + r * l * Math.cos(angles[i])
                      const y = cy + r * l * Math.sin(angles[i])
                      return `${x},${y}`
                    }).join(' ')
                    return <polygon key={l} points={pts} fill="none" stroke="#ddd" strokeWidth={1} />
                  })

                  const axisLines = radarData.map((_, i) => {
                    const x = cx + r * Math.cos(angles[i])
                    const y = cy + r * Math.sin(angles[i])
                    return <line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke="#ddd" strokeWidth={1} />
                  })

                  const v1Points = radarData.map((v, i) => {
                    const ratio = v.v1 / maxRadar
                    const x = cx + r * ratio * Math.cos(angles[i])
                    const y = cy + r * ratio * Math.sin(angles[i])
                    return `${x},${y}`
                  }).join(' ')

                  const v2Points = radarData.map((v, i) => {
                    const ratio = v.v2 / maxRadar
                    const x = cx + r * ratio * Math.cos(angles[i])
                    const y = cy + r * ratio * Math.sin(angles[i])
                    return `${x},${y}`
                  }).join(' ')

                  const labels = radarData.map((v, i) => {
                    const lx = cx + (r + 20) * Math.cos(angles[i])
                    const ly = cy + (r + 20) * Math.sin(angles[i])
                    return (
                      <text key={i} x={lx} y={ly} textAnchor="middle" dominantBaseline="middle" fontSize={10} fill="#666">
                        {v.label}
                      </text>
                    )
                  })

                  return (
                    <>
                      {gridLines}
                      {axisLines}
                      {labels}
                      <polygon points={v1Points} fill="rgba(25,135,84,0.2)" stroke="#198754" strokeWidth={2} />
                      <polygon points={v2Points} fill="rgba(220,53,69,0.2)" stroke="#dc3545" strokeWidth={2} />
                      <circle cx={10} cy={10} r={4} fill="#198754" />
                      <text x={20} y={14} fontSize={10} fill="#198754">{comparacion.equipo1.nombre}</text>
                      <circle cx={10} cy={26} r={4} fill="#dc3545" />
                      <text x={20} y={30} fontSize={10} fill="#dc3545">{comparacion.equipo2.nombre}</text>
                    </>
                  )
                })()}
              </svg>
            </div>

            {/* H2H */}
            {comparacion.h2h.matches.length > 0 && (
              <div className="mt-4">
                <h6 className="fw-semibold mb-2">Historial H2H</h6>
                <div className="d-flex gap-3 mb-3">
                  <span className="badge bg-success">{comparacion.equipo1.nombre}: {comparacion.h2h.eq1_wins}V</span>
                  <span className="badge bg-warning text-dark">Empates: {comparacion.h2h.draws}</span>
                  <span className="badge bg-danger">{comparacion.equipo2.nombre}: {comparacion.h2h.eq2_wins}V</span>
                </div>
                <div className="vstack gap-1 small">
                  {comparacion.h2h.matches.map((m, i) => (
                    <div key={i} className="d-flex justify-content-between">
                      <span className="fw-semibold">{m.eq1_goals} - {m.eq2_goals}</span>
                      <span className="text-muted">{m.fecha ? new Date(m.fecha).toLocaleDateString('es-AR') : '-'}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  )
}
